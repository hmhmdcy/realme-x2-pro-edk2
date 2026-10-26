using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices.WindowsRuntime;
using System.Text;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using Windows.Devices.Bluetooth;
using Windows.Devices.Bluetooth.Advertisement;
using Windows.Devices.Bluetooth.GenericAttributeProfile;
using Windows.Foundation;

// One private, addressed test peer. No pairing, radio changes or connection retries.
public sealed class SamuraiGattCentral
{
    private static readonly Guid ServiceUuid = new Guid("f0d19310-7a52-4d3f-9b14-0e4bb7f30001");
    private static readonly Guid RxUuid = new Guid("f0d19310-7a52-4d3f-9b14-0e4bb7f30002");
    private static readonly Guid TxUuid = new Guid("f0d19310-7a52-4d3f-9b14-0e4bb7f30003");
    private static readonly byte[] Prefix = Encoding.ASCII.GetBytes("RMX1931-LE:");
    private const string PrivateRoot = @"E:\edk2-samurai-out\bluetooth-windows-central-20261023";
    private readonly object gate = new object();
    private readonly Dictionary<string, object> report = new Dictionary<string, object>();
    private readonly List<Dictionary<string, object>> operations = new List<Dictionary<string, object>>();
    private readonly List<Dictionary<string, object>> exchanges = new List<Dictionary<string, object>>();
    private readonly List<string> cleanupErrors = new List<string>();
    private readonly List<string> connectionStates = new List<string>();
    private readonly List<GattDeviceService> services = new List<GattDeviceService>();
    private BluetoothLEAdvertisementWatcher watcher;
    private TypedEventHandler<BluetoothLEAdvertisementWatcher, BluetoothLEAdvertisementReceivedEventArgs> receivedHandler;
    private TypedEventHandler<BluetoothLEAdvertisementWatcher, BluetoothLEAdvertisementWatcherStoppedEventArgs> stoppedHandler;
    private TypedEventHandler<GattCharacteristic, GattValueChangedEventArgs> notificationHandler;
    private TypedEventHandler<BluetoothLEDevice, object> connectionHandler;
    private readonly TaskCompletionSource<bool> watcherStopped = new TaskCompletionSource<bool>();
    private readonly TaskCompletionSource<BluetoothAddressType> found = new TaskCompletionSource<BluetoothAddressType>();
    private BluetoothLEDevice device;
    private GattSession session;
    private GattCharacteristic rx, tx;
    private TaskCompletionSource<byte[]> expectedNotification;
    private byte[] expectedPayload;
    private ulong expectedAddress;
    private int serviceAdvertisements, matchingAdvertisements, notificationCount, otherNotifications;
    private bool watcherStarted, subscribed, cleaningUp;
    private string watcherStopError;
    private readonly Stopwatch elapsed = new Stopwatch();
    private int totalBudgetMilliseconds;
    private int operationTimeout = 10000;
    private int scanTimeout = 10000;

    public static int Main(string[] args)
    {
        try { return new SamuraiGattCentral().Run(args).GetAwaiter().GetResult(); }
        catch (Exception e) { Console.Error.WriteLine("Central setup failed: " + e.GetType().Name); return 2; }
    }

    private static string PrivatePath(string value)
    {
        string path = Path.GetFullPath(value);
        if (!path.StartsWith(PrivateRoot + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase))
            throw new ArgumentException("Use the dedicated private output directory");
        return path;
    }

    private static int Option(Dictionary<string, object> config, string key, int fallback, int min, int max)
    {
        object value;
        int result = config.TryGetValue(key, out value) ? Convert.ToInt32(value) : fallback;
        if (result < min || result > max) throw new ArgumentException("Invalid bounded option: " + key);
        return result;
    }

    private async Task<int> Run(string[] args)
    {
        bool probe = args.Length == 2 && args[0] == "--probe";
        bool run = args.Length == 3 && args[0] == "--run";
        if (!probe && !run) throw new ArgumentException("--probe PRIVATE_RESULT or --run PRIVATE_CONFIG PRIVATE_RESULT");
        Directory.CreateDirectory(PrivateRoot);
        string output = PrivatePath(args[probe ? 1 : 2]);
        if (File.Exists(output)) throw new ArgumentException("Result already exists; do not replay over evidence");
        int shortSequence = 1, longSequence = 2, totalSeconds = 120;
        if (run)
        {
            var serializer = new JavaScriptSerializer();
            var config = serializer.Deserialize<Dictionary<string, object>>(File.ReadAllText(PrivatePath(args[1])));
            object value;
            if (!config.TryGetValue("server_window_confirmed", out value) || !(value is bool) || !(bool)value)
                throw new ArgumentException("A confirmed phone server window is required");
            string address = config.ContainsKey("expected_address") ? Convert.ToString(config["expected_address"]) : "";
            if (address.Length != 12 || !address.All(Uri.IsHexDigit) ||
                !ulong.TryParse(address, System.Globalization.NumberStyles.HexNumber,
                    System.Globalization.CultureInfo.InvariantCulture, out expectedAddress) || expectedAddress == 0)
                throw new ArgumentException("Private expected_address must be exactly 12 hexadecimal digits");
            operationTimeout = Option(config, "operation_timeout_ms", 10000, 1000, 20000);
            scanTimeout = Option(config, "scan_timeout_ms", 10000, 1000, 20000);
            totalSeconds = Option(config, "total_timeout_seconds", 120, 20, 180);
            shortSequence = Option(config, "short_sequence", 1, 1, 16);
            longSequence = Option(config, "long_sequence", 2, 1, 16);
            if (shortSequence == longSequence) throw new ArgumentException("Distinct short/long sequences required");
            report["expected_phone_address_private"] = expectedAddress.ToString("X12");
        }
        totalBudgetMilliseconds = (probe ? 15 : totalSeconds) * 1000;
        elapsed.Start();
        report["mode"] = probe ? "probe" : "run";
        report["started_utc"] = DateTime.UtcNow.ToString("o");
        report["service_uuid"] = ServiceUuid.ToString();
        report["operations"] = operations;
        report["exchanges"] = exchanges;
        report["connection_states"] = connectionStates;
        report["cleanup_errors"] = cleanupErrors;
        report["pairing_requested"] = false;
        report["device_creation_calls"] = 0;
        report["connection_process_cancellable"] = false;
        report["cancellation_is_not_connection_end_proof"] = true;
        report["physical_disconnect_confirmed"] = false;
        bool passed = false;
        try
        {
            BluetoothAdapter adapter = await Await(BluetoothAdapter.GetDefaultAsync(), "get_local_adapter", operationTimeout);
            if (adapter == null) throw new InvalidOperationException("No Windows Bluetooth adapter");
            report["local_adapter_address_private"] = adapter.BluetoothAddress.ToString("X12");
            report["central_supported"] = adapter.IsCentralRoleSupported;
            if (!adapter.IsCentralRoleSupported) throw new InvalidOperationException("Central role unavailable");
            StartWatcher(!probe);
            if (probe)
            {
                await Task.Delay(1000);
                report["watcher_active_status"] = watcher.Status.ToString();
                if (watcher.Status != BluetoothLEAdvertisementWatcherStatus.Started)
                    throw new InvalidOperationException("Watcher did not remain Started");
                passed = true;
            }
            else
            {
                BluetoothAddressType addressType = await WaitFor(found.Task, "addressed_service_advertisement", scanTimeout);
                await StopWatcher();
                report["matched_address_type"] = addressType.ToString();
                report["device_creation_calls"] = 1;
                device = await Await(BluetoothLEDevice.FromBluetoothAddressAsync(expectedAddress, addressType),
                                     "from_expected_address", operationTimeout);
                if (device == null) throw new InvalidOperationException("Expected device was not available");
                if (device.BluetoothAddress != expectedAddress) throw new InvalidOperationException("Unexpected device identity");
                connectionHandler = (sender, ev) => { lock (gate) connectionStates.Add(sender.ConnectionStatus.ToString()); };
                device.ConnectionStatusChanged += connectionHandler;
                session = await Await(GattSession.FromDeviceIdAsync(device.BluetoothDeviceId), "create_session", operationTimeout);
                if (session == null) throw new InvalidOperationException("No GATT session");
                session.MaintainConnection = false;
                var discovered = await Await(device.GetGattServicesForUuidAsync(ServiceUuid, BluetoothCacheMode.Uncached),
                                             "uncached_service_discovery", operationTimeout);
                services.AddRange(discovered.Services);
                Check(discovered.Status, "Service discovery");
                if (services.Count != 1) throw new InvalidOperationException("Expected exactly one dedicated service");
                rx = await Characteristic(services[0], RxUuid, "rx");
                tx = await Characteristic(services[0], TxUuid, "tx");
                if ((rx.CharacteristicProperties & (GattCharacteristicProperties.Read | GattCharacteristicProperties.Write)) !=
                    (GattCharacteristicProperties.Read | GattCharacteristicProperties.Write))
                    throw new InvalidOperationException("RX requires Read and WriteWithResponse support");
                if ((tx.CharacteristicProperties & (GattCharacteristicProperties.Read | GattCharacteristicProperties.Notify)) !=
                    (GattCharacteristicProperties.Read | GattCharacteristicProperties.Notify))
                    throw new InvalidOperationException("TX requires Read and Notify support");
                byte[] initial = await Read(tx, "initial_tx");
                if (!initial.SequenceEqual(Encoding.ASCII.GetBytes("RMX1931-LE:READY")))
                    throw new InvalidDataException("TX initial READY value mismatch");
                report["initial_tx_ready_matched"] = true;
                notificationHandler = OnNotification;
                tx.ValueChanged += notificationHandler;
                Check(await Await(tx.WriteClientCharacteristicConfigurationDescriptorAsync(
                      GattClientCharacteristicConfigurationDescriptorValue.Notify), "subscribe_tx_notify", operationTimeout), "Subscribe");
                subscribed = true;
                report["notify_subscription_succeeded"] = true;
                await Exchange(shortSequence, 5);
                report["max_pdu_size_after_short_exchange"] = session.MaxPduSize;
                if (session.MaxPduSize >= 50)
                {
                    await Exchange(longSequence, 32);
                    report["extended_47_bytes"] = "passed";
                }
                else report["extended_47_bytes"] = "not_run_max_pdu_below_50";
                report["connection_status_before_cleanup"] = device.ConnectionStatus.ToString();
                passed = true;
            }
        }
        catch (Exception e)
        {
            report["error_type"] = e.GetType().FullName;
            report["error_private"] = e.Message;
        }
        // The installed framework compiler is C# 5 (no await in finally).
        // All operation failures above are caught before this single cleanup path.
        {
            cleaningUp = true;
            lock (gate) { expectedNotification = null; expectedPayload = null; }
            if (tx != null && subscribed)
            {
                try
                {
                    GattCommunicationStatus status = await Await(tx.WriteClientCharacteristicConfigurationDescriptorAsync(
                        GattClientCharacteristicConfigurationDescriptorValue.None), "unsubscribe_tx_notify", 4000);
                    report["unsubscribe_status"] = status.ToString();
                    if (status != GattCommunicationStatus.Success) cleanupErrors.Add("unsubscribe:" + status);
                }
                catch (Exception e) { cleanupErrors.Add("unsubscribe:" + e.GetType().Name); }
            }
            if (tx != null && notificationHandler != null)
                try { tx.ValueChanged -= notificationHandler; } catch (Exception e) { cleanupErrors.Add("remove_notify_handler:" + e.GetType().Name); }
            foreach (GattDeviceService service in services)
                try { service.Dispose(); } catch (Exception e) { cleanupErrors.Add("service_dispose:" + e.GetType().Name); }
            report["service_references_disposed"] = services.Count;
            if (session != null)
                try { session.MaintainConnection = false; session.Dispose(); } catch (Exception e) { cleanupErrors.Add("session_dispose:" + e.GetType().Name); }
            report["session_reference_disposed"] = session != null;
            if (device != null)
            {
                try
                {
                    report["connection_status_at_reference_release"] = device.ConnectionStatus.ToString();
                    if (connectionHandler != null) device.ConnectionStatusChanged -= connectionHandler;
                    device.Dispose();
                }
                catch (Exception e) { cleanupErrors.Add("device_dispose:" + e.GetType().Name); }
            }
            report["device_reference_disposed"] = device != null;
            try { await StopWatcher(); } catch (Exception e) { cleanupErrors.Add("watcher_stop:" + e.GetType().Name); }
            if (watcher != null)
            {
                try { if (receivedHandler != null) watcher.Received -= receivedHandler; }
                catch (Exception e) { cleanupErrors.Add("remove_watcher_received:" + e.GetType().Name); }
                try { if (stoppedHandler != null) watcher.Stopped -= stoppedHandler; }
                catch (Exception e) { cleanupErrors.Add("remove_watcher_stopped:" + e.GetType().Name); }
                report["watcher_final_status"] = watcher.Status.ToString();
            }
            lock (gate)
            {
                report["service_filtered_advertisements"] = serviceAdvertisements;
                report["matched_expected_advertisements"] = matchingAdvertisements;
                report["notification_count"] = notificationCount;
                report["other_notifications"] = otherNotifications;
                report["watcher_stop_error"] = watcherStopError;
                report["async_operations_without_terminal_status"] = operations.Count(o =>
                    !o.ContainsKey("operation_terminal") || !(bool)o["operation_terminal"]);
                report["terminal"] = true;
                report["passed"] = passed && cleanupErrors.Count == 0;
                report["completed_utc"] = DateTime.UtcNow.ToString("o");
                report["dispose_is_not_physical_disconnect_proof"] = true;
                File.WriteAllText(output, new JavaScriptSerializer().Serialize(report), new UTF8Encoding(false));
            }
        }
        Console.WriteLine(new JavaScriptSerializer().Serialize(new {
            mode = probe ? "probe" : "run", passed = passed && cleanupErrors.Count == 0,
            device_creation_calls = report["device_creation_calls"],
            phone_gatt_test_executed = !probe && exchanges.Count > 0,
            physical_disconnect_confirmed = false
        }));
        return passed && cleanupErrors.Count == 0 ? 0 : 1;
    }

    private void StartWatcher(bool addressed)
    {
        watcher = new BluetoothLEAdvertisementWatcher();
        watcher.AdvertisementFilter.Advertisement.ServiceUuids.Add(ServiceUuid);
        watcher.ScanningMode = BluetoothLEScanningMode.Active;
        receivedHandler = (sender, args) => {
            try
            {
                if (!args.Advertisement.ServiceUuids.Contains(ServiceUuid)) return;
                lock (gate)
                {
                    serviceAdvertisements++;
                    if (addressed && args.BluetoothAddress == expectedAddress)
                    {
                        matchingAdvertisements++;
                        found.TrySetResult(args.BluetoothAddressType);
                    }
                }
            }
            catch (Exception e) { lock (gate) report["watcher_callback_error"] = e.GetType().Name; }
        };
        stoppedHandler = (sender, args) => {
            lock (gate) watcherStopError = args.Error.ToString();
            watcherStopped.TrySetResult(true);
            if (addressed) found.TrySetException(new InvalidOperationException("Watcher stopped before expected peer was found"));
        };
        watcher.Received += receivedHandler;
        watcher.Stopped += stoppedHandler;
        watcher.Start();
        watcherStarted = true;
        report["watcher_start_status"] = watcher.Status.ToString();
    }

    private async Task StopWatcher()
    {
        if (watcher == null || !watcherStarted) return;
        if (watcher.Status == BluetoothLEAdvertisementWatcherStatus.Started) watcher.Stop();
        if (watcher.Status == BluetoothLEAdvertisementWatcherStatus.Stopping)
            await WaitFor(watcherStopped.Task, "watcher_stopped", 2000);
        watcherStarted = false;
        if (watcher.Status != BluetoothLEAdvertisementWatcherStatus.Stopped)
            throw new InvalidOperationException("Watcher did not finish Stopped: " + watcher.Status);
    }

    private async Task<GattCharacteristic> Characteristic(GattDeviceService service, Guid uuid, string label)
    {
        var result = await Await(service.GetCharacteristicsForUuidAsync(uuid, BluetoothCacheMode.Uncached),
                                 "uncached_" + label + "_discovery", operationTimeout);
        Check(result.Status, label + " discovery");
        if (result.Characteristics.Count != 1) throw new InvalidOperationException("Expected exactly one " + label);
        return result.Characteristics[0];
    }

    private async Task<byte[]> Read(GattCharacteristic characteristic, string name)
    {
        GattReadResult result = await Await(characteristic.ReadValueAsync(BluetoothCacheMode.Uncached), name, operationTimeout);
        Check(result.Status, name);
        return result.Value.ToArray();
    }

    private async Task Exchange(int sequence, int tailBytes)
    {
        byte[] payload = new byte[Prefix.Length + 4 + tailBytes];
        Array.Copy(Prefix, payload, Prefix.Length);
        uint seq = (uint)sequence;
        for (int i = 0; i < 4; i++) payload[Prefix.Length + i] = (byte)(seq >> (8 * i));
        for (int i = 0; i < tailBytes; i++) payload[Prefix.Length + 4 + i] = (byte)i;
        var record = new Dictionary<string, object> { { "sequence", sequence }, { "bytes", payload.Length },
            { "notify_exact", false }, { "rx_read_exact", false }, { "tx_read_exact", false } };
        exchanges.Add(record);
        TaskCompletionSource<byte[]> wait = new TaskCompletionSource<byte[]>();
        lock (gate) { expectedPayload = payload; expectedNotification = wait; }
        try
        {
            GattWriteResult result = await Await(rx.WriteValueWithResultAsync(payload.AsBuffer(), GattWriteOption.WriteWithResponse),
                                                 "write_rx_seq_" + sequence, operationTimeout);
            record["write_status"] = result.Status.ToString();
            if (result.ProtocolError.HasValue) record["write_protocol_error"] = result.ProtocolError.Value;
            Check(result.Status, "Write RX");
            byte[] notification = await WaitFor(wait.Task, "notify_seq_" + sequence, operationTimeout);
            if (!notification.SequenceEqual(payload)) throw new InvalidDataException("Notification payload mismatch");
            record["notify_exact"] = true;
            byte[] readRx = await Read(rx, "read_rx_seq_" + sequence);
            if (!readRx.SequenceEqual(payload)) throw new InvalidDataException("RX read payload mismatch");
            record["rx_read_exact"] = true;
            byte[] readTx = await Read(tx, "read_tx_seq_" + sequence);
            if (!readTx.SequenceEqual(payload)) throw new InvalidDataException("TX read payload mismatch");
            record["tx_read_exact"] = true;
            record["passed"] = true;
        }
        finally { lock (gate) { expectedPayload = null; expectedNotification = null; } }
    }

    private void OnNotification(GattCharacteristic sender, GattValueChangedEventArgs args)
    {
        try
        {
            byte[] bytes = args.CharacteristicValue.ToArray();
            lock (gate)
            {
                notificationCount++;
                if (expectedPayload == null || expectedNotification == null || bytes.Length < Prefix.Length + 4 ||
                    !bytes.Take(Prefix.Length + 4).SequenceEqual(expectedPayload.Take(Prefix.Length + 4)))
                { otherNotifications++; return; }
                if (bytes.SequenceEqual(expectedPayload)) expectedNotification.TrySetResult(bytes);
                else expectedNotification.TrySetException(new InvalidDataException("Same-sequence notification was not complete and exact"));
            }
        }
        catch (Exception e) { lock (gate) { if (expectedNotification != null) expectedNotification.TrySetException(e); } }
    }

    private int Budget(int requested)
    {
        long available = totalBudgetMilliseconds - elapsed.ElapsedMilliseconds;
        if (!cleaningUp && available <= 0) throw new TimeoutException("Overall test deadline reached; no retry");
        return cleaningUp ? requested : (int)Math.Min((long)requested, available);
    }

    private async Task<T> WaitFor<T>(Task<T> task, string label, int milliseconds)
    {
        int timeout = Budget(milliseconds);
        if (await Task.WhenAny(task, Task.Delay(timeout)) != task)
            throw new TimeoutException(label + " timed out; no retry");
        return await task;
    }

    private async Task<T> Await<T>(IAsyncOperation<T> operation, string label, int milliseconds)
    {
        var record = new Dictionary<string, object> { { "operation", label }, { "completed", false },
            { "cancel_requested", false }, { "timeout", false } };
        operations.Add(record);
        Task<T> task = operation.AsTask();
        bool lateObserverScheduled = false;
        try
        {
            if (await Task.WhenAny(task, Task.Delay(Budget(milliseconds))) != task)
            {
                record["timeout"] = true;
                record["cancel_requested"] = true;
                try { operation.Cancel(); } catch (Exception e) { record["cancel_error"] = e.GetType().Name; }
                try { record["status_after_cancel_request"] = operation.Status.ToString(); } catch (Exception e) { record["status_error"] = e.GetType().Name; }
                record["completion_after_timeout_not_assumed"] = true;
                ObserveLate(task, record);
                lateObserverScheduled = true;
                throw new TimeoutException(label + " timed out; cancellation is not completion proof; no retry");
            }
            T result = await task;
            record["completed"] = true;
            record["status"] = operation.Status.ToString();
            return result;
        }
        catch (Exception e)
        {
            record["error_type"] = e.GetType().Name;
            if (!task.IsCompleted && !lateObserverScheduled)
            {
                record["cancel_requested"] = true;
                try { operation.Cancel(); } catch (Exception cancel) { record["cancel_error"] = cancel.GetType().Name; }
                ObserveLate(task, record);
            }
            throw;
        }
        finally
        {
            try
            {
                record["operation_status_at_release"] = operation.Status.ToString();
                record["operation_terminal"] = operation.Status != AsyncStatus.Started;
            }
            catch (Exception e) { record["status_error"] = e.GetType().Name; record["operation_terminal"] = false; }
        }
    }

    private void ObserveLate<T>(Task<T> task, Dictionary<string, object> record)
    {
        // A continuation is best-effort cleanup while this process remains alive.
        // The final receipt never treats cancellation as physical disconnection.
        Task lateCleanup = task.ContinueWith(t => {
            try
            {
                if (t.IsFaulted) { var observed = t.Exception; return; }
                if (t.Status != TaskStatus.RanToCompletion) return;
                object value = t.Result;
                var lateServices = value as GattDeviceServicesResult;
                if (lateServices != null) foreach (var service in lateServices.Services) service.Dispose();
                var disposable = value as IDisposable;
                if (disposable != null) disposable.Dispose();
            }
            catch { /* It may finish after the terminal receipt; do not assert success. */ }
        });
        record["late_result_cleanup_scheduled"] = lateCleanup != null;
    }

    private static void Check(GattCommunicationStatus status, string label)
    {
        if (status != GattCommunicationStatus.Success) throw new InvalidOperationException(label + ": " + status);
    }
}
