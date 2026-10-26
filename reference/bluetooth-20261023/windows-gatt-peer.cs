using System;
using System.IO;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Runtime.InteropServices.WindowsRuntime;
using Windows.Devices.Bluetooth;
using Windows.Devices.Bluetooth.GenericAttributeProfile;

// A dedicated, bounded peer. No pairing, user-data access or persistent service.
public static class SamuraiGattPeer
{
    public static int Main(string[] args)
    {
        try { return Run(args).GetAwaiter().GetResult(); }
        catch (Exception e) { Console.Error.WriteLine(e.ToString()); return 1; }
    }

    private static async Task<int> Run(string[] args)
    {
        if (args.Length != 2) throw new ArgumentException("duration and private state path required");
        int duration = int.Parse(args[0]);
        if (duration < 1 || duration > 300) throw new ArgumentException("duration 1..300 required");
        string statePath = args[1];
        var serviceUuid = new Guid("f83b8821-f878-46e2-9f51-47da7b509601");
        var characteristicUuid = new Guid("f83b8821-f878-46e2-9f51-47da7b509602");
        var created = await GattServiceProvider.CreateAsync(serviceUuid);
        if (created.Error != BluetoothError.Success)
            throw new InvalidOperationException("Create GATT provider: " + created.Error);
        var provider = created.ServiceProvider;
        string lastError = "None";
        var advertisementChanged = new TaskCompletionSource<string>();
        provider.AdvertisementStatusChanged += (sender, eventArgs) => {
            lastError = eventArgs.Error.ToString();
            advertisementChanged.TrySetResult(eventArgs.Status.ToString());
        };
        bool started = false;
        try
        {
            var parameters = new GattLocalCharacteristicParameters {
                CharacteristicProperties = GattCharacteristicProperties.Read,
                ReadProtectionLevel = GattProtectionLevel.Plain,
                StaticValue = Encoding.ASCII.GetBytes("samurai-bt-gatt-v1").AsBuffer()
            };
            var characteristic = await provider.Service.CreateCharacteristicAsync(characteristicUuid, parameters);
            if (characteristic.Error != BluetoothError.Success)
                throw new InvalidOperationException("Create characteristic: " + characteristic.Error);
            provider.StartAdvertising(new GattServiceProviderAdvertisingParameters {
                IsConnectable = true, IsDiscoverable = true
            });
            started = true;
            if (await Task.WhenAny(advertisementChanged.Task, Task.Delay(5000)) != advertisementChanged.Task)
                throw new InvalidOperationException("No GATT advertisement status callback");
            if (provider.AdvertisementStatus == GattServiceProviderAdvertisementStatus.Aborted)
                throw new InvalidOperationException("GATT advertising aborted: " + lastError);
            DateTime deadline = DateTime.UtcNow.AddSeconds(duration);
            do
            {
                File.WriteAllText(statePath, State(provider, false, false));
                await Task.Delay(250);
            } while (DateTime.UtcNow < deadline && !File.Exists(Path.Combine(Path.GetDirectoryName(statePath), "windows-peer-stop")));
            return 0;
        }
        finally
        {
            if (started) provider.StopAdvertising();
            File.WriteAllText(statePath, State(provider, true, started));
        }
    }

    private static string State(GattServiceProvider provider, bool terminal, bool stopped)
    {
        return "{\"terminal\":" + terminal.ToString().ToLowerInvariant() +
            ",\"stopped\":" + stopped.ToString().ToLowerInvariant() +
            ",\"advertising_status\":\"" + provider.AdvertisementStatus +
            "\",\"pid\":" + System.Diagnostics.Process.GetCurrentProcess().Id +
            ",\"service_uuid\":\"f83b8821-f878-46e2-9f51-47da7b509601\"}";
    }
}
