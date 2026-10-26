// Fixed SDK 10.0.26100 user-mode pshpack1 layouts; only two GET IOCTLs.
using System;
using System.ComponentModel;
using System.IO;
using System.Runtime.InteropServices;
using Microsoft.Win32.SafeHandles;

namespace SamuraiUsb500 {
    public sealed class HubInfo {
        public int Ports;
        public bool BusPowered;
        public int ControllerCurrentMa;
    }
    public sealed class PortInfo {
        public uint Port;
        public uint Status;
        public string StatusName;
        public string EvidenceClass;
        public string Vendor;
        public string Product;
        public byte Configuration;
        public byte Speed;
        public bool IsHub;
        public ushort Address;
        public uint OpenPipes;
        public bool DescriptorValid;
        public string DescriptorWarning;
    }
    public static class Decode {
        public const uint GetNode = 0x220408;
        public const uint GetConnectionEx = 0x220448;
        static void Need(bool value, string message) {
            if (!value) throw new InvalidDataException(message);
        }
        public static void Allowed(uint code) {
            Need(code == GetNode || code == GetConnectionEx, "Only two read-only GET IOCTLs allowed");
        }
        public static HubInfo Hub(byte[] data) {
            Need(data != null && data.Length == 76, "Node response must match 76-byte SDK layout");
            Need(BitConverter.ToUInt32(data, 0) == 0, "Expected UsbHub union, not UsbMIParent");
            Need(data[4] >= 9 && data[4] <= 71 && data[5] == 0x29, "USB 2 hub descriptor");
            Need(data[6] >= 1 && data[6] <= 15 && data[75] <= 1, "Bounded hub ports/BOOLEAN");
            return new HubInfo { Ports = data[6], BusPowered = data[75] != 0, ControllerCurrentMa = data[10] };
        }
        public static string StatusName(uint status) {
            string[] names = { "NoDeviceConnected", "DeviceConnected", "DeviceFailedEnumeration",
                "DeviceGeneralFailure", "DeviceCausedOvercurrent", "DeviceNotEnoughPower",
                "DeviceNotEnoughBandwidth", "DeviceHubNestedTooDeeply", "DeviceInLegacyHub",
                "DeviceEnumerating", "DeviceReset" };
            return status < names.Length ? names[status] : "Unknown(" + status + ")";
        }
        public static string Evidence(uint status) {
            switch (status) {
            case 0: return "absent";
            case 1: return "connected";
            case 2: return "enumeration_failure";
            case 3: return "general_failure";
            case 4: return "overcurrent";
            case 5: return "explicit_host_power_rejection";
            case 6: return "bandwidth_failure";
            case 7: return "hub_depth_failure";
            case 8: return "legacy_hub_failure";
            case 9: return "enumerating_transient";
            case 10: return "reset_transient";
            default: return "unknown_status";
            }
        }
        public static PortInfo Port(byte[] data, uint expectedPort) {
            Need(expectedPort >= 1 && expectedPort <= 15, "Bounded one-hub connection index");
            Need(data != null && data.Length >= 35 && data.Length <= 512, "35-byte connection header and bounded response");
            uint index = BitConverter.ToUInt32(data, 0);
            Need(index == expectedPort, "ConnectionIndex response mismatch");
            Need(data[24] <= 1, "DeviceIsHub BOOLEAN");
            uint pipes = BitConverter.ToUInt32(data, 27);
            // USB_PIPE_INFO is 7-byte endpoint descriptor + 4-byte offset.
            Need(pipes <= 43 && 35L + 11L * pipes <= data.Length, "Truncated/overflowed PipeList");
            uint status = BitConverter.ToUInt32(data, 31); // NOT offset 32
            bool descriptor = data[4] == 18 && data[5] == 1 && data[21] != 0;
            return new PortInfo { Port = index, Status = status, StatusName = StatusName(status),
                EvidenceClass = Evidence(status), Vendor = BitConverter.ToUInt16(data, 12).ToString("x4"),
                Product = BitConverter.ToUInt16(data, 14).ToString("x4"), Configuration = data[22],
                Speed = data[23], IsHub = data[24] != 0, Address = BitConverter.ToUInt16(data, 25),
                OpenPipes = pipes, DescriptorValid = descriptor,
                DescriptorWarning = descriptor ? null : "Descriptor unavailable/invalid; status retained, not an identity match" };
        }
        public static bool Target(PortInfo port) {
            return port.Status == 1 && port.DescriptorValid && !port.IsHub
                && port.Configuration == 1 && port.Vendor == "0525" && port.Product == "a4a1";
        }
    }

    public sealed class UnresolvedReadException : IOException {
        public UnresolvedReadException(string text) : base(text) { }
    }

    public sealed class HubSession : IDisposable {
        [StructLayout(LayoutKind.Sequential)]
        struct Overlapped {
            public UIntPtr Internal, InternalHigh;
            public uint Offset, OffsetHigh;
            public IntPtr Event;
        }
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        static extern SafeFileHandle CreateFile(string path, uint access, uint share,
            IntPtr security, uint disposition, uint flags, IntPtr template);
        [DllImport("kernel32.dll", SetLastError = true)]
        static extern bool DeviceIoControl(SafeFileHandle handle, uint code, IntPtr input,
            uint inputSize, IntPtr output, uint outputSize, IntPtr bytesReturned, IntPtr overlapped);
        [DllImport("kernel32.dll", SetLastError = true)]
        static extern IntPtr CreateEvent(IntPtr security, bool manual, bool initial, string name);
        [DllImport("kernel32.dll", SetLastError = true)]
        static extern uint WaitForSingleObject(IntPtr handle, uint milliseconds);
        [DllImport("kernel32.dll", SetLastError = true)]
        static extern bool GetOverlappedResult(SafeFileHandle handle, IntPtr overlapped, out uint bytes, bool wait);
        [DllImport("kernel32.dll", SetLastError = true)]
        static extern bool CancelIoEx(SafeFileHandle handle, IntPtr overlapped);
        [DllImport("kernel32.dll", SetLastError = true)]
        static extern bool CloseHandle(IntPtr handle);
        readonly SafeFileHandle handle;
        bool unresolved;

        public HubSession(string path) {
            if (!BitConverter.IsLittleEndian) throw new PlatformNotSupportedException("Windows little endian layout required");
            // Zero desired access, share read/write, OPEN_EXISTING; OVERLAPPED
            // bounds GET latency. No port/controller operation is submitted.
            handle = CreateFile(path, 0, 3, IntPtr.Zero, 3, 0x40000080, IntPtr.Zero);
            if (handle.IsInvalid) throw new Win32Exception(Marshal.GetLastWin32Error());
        }
        public byte[] Query(uint code, uint port, int timeoutMs) {
            Decode.Allowed(code);
            if (unresolved) throw new UnresolvedReadException("Earlier read cancellation unresolved; no more queries");
            if (timeoutMs < 1 || timeoutMs > 500) throw new ArgumentOutOfRangeException("timeoutMs");
            if (code == Decode.GetConnectionEx && (port < 1 || port > 15)) throw new ArgumentOutOfRangeException("port");
            int size = code == Decode.GetNode ? 76 : 512;
            byte[] input = new byte[size];
            if (code == Decode.GetConnectionEx) Array.Copy(BitConverter.GetBytes(port), input, 4);
            IntPtr buffer = Marshal.AllocHGlobal(size);
            IntPtr overlap = Marshal.AllocHGlobal(Marshal.SizeOf(typeof(Overlapped)));
            IntPtr done = CreateEvent(IntPtr.Zero, true, false, null);
            bool safeToFree = true;
            try {
                if (done == IntPtr.Zero) throw new Win32Exception(Marshal.GetLastWin32Error());
                Marshal.Copy(input, 0, buffer, size);
                Marshal.StructureToPtr(new Overlapped { Event = done }, overlap, false);
                bool immediate = DeviceIoControl(handle, code, buffer, (uint)size, buffer, (uint)size, IntPtr.Zero, overlap);
                int error = immediate ? 0 : Marshal.GetLastWin32Error();
                if (!immediate && error != 997) throw new Win32Exception(error);
                if (!immediate && WaitForSingleObject(done, (uint)timeoutMs) != 0) {
                    // Cancels only this host GET request; does not reset USB.
                    CancelIoEx(handle, overlap);
                    if (WaitForSingleObject(done, 250) != 0) {
                        unresolved = true;
                        safeToFree = false; // native IO may still reference these buffers
                        throw new UnresolvedReadException("GET cancellation not completed; abort this process; retain buffers until process exit");
                    }
                    uint ignored;
                    if (!GetOverlappedResult(handle, overlap, out ignored, false) && Marshal.GetLastWin32Error() == 996) {
                        unresolved = true;
                        safeToFree = false;
                        throw new UnresolvedReadException("GET still incomplete after cancellation");
                    }
                    throw new TimeoutException("Read-only hub GET deadline exceeded");
                }
                uint returned;
                if (!GetOverlappedResult(handle, overlap, out returned, false)) {
                    int completionError = Marshal.GetLastWin32Error();
                    if (completionError == 996) {
                        unresolved = true;
                        safeToFree = false;
                        throw new UnresolvedReadException("Completion still pending; native buffers retained");
                    }
                    throw new Win32Exception(completionError);
                }
                int minimum = code == Decode.GetNode ? 76 : 35;
                if (returned < minimum || returned > size) throw new InvalidDataException("GET response size outside requested structure");
                byte[] output = new byte[returned];
                Marshal.Copy(buffer, output, 0, (int)returned);
                return output;
            } finally {
                if (safeToFree) {
                    if (done != IntPtr.Zero) CloseHandle(done);
                    Marshal.FreeHGlobal(overlap);
                    Marshal.FreeHGlobal(buffer);
                }
                // On unresolved cancellation close the process promptly. These
                // allocations/event intentionally remain live until OS teardown.
            }
        }
        public void Dispose() { handle.Dispose(); }
    }
}
