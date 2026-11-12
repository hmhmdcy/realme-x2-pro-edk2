param(
    [string]$InstanceId = "USB\VID_0525&PID_A4A1\62BC28A1",
    [int]$Port = 0,
    [switch]$Cycle,
    [switch]$QueryOnly,
    [string]$LogPath = "usb-port-cycle.txt"
)

$ErrorActionPreference = "Stop"

$source = @'
using System;
using System.Runtime.InteropServices;
using Microsoft.Win32.SafeHandles;

public static class UsbHubPort {
    [DllImport("kernel32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    public static extern SafeFileHandle CreateFile(
        string name, uint access, uint share, IntPtr sec,
        uint disp, uint flags, IntPtr tmpl);

    [DllImport("kernel32.dll", SetLastError = true)]
    public static extern bool DeviceIoControl(
        SafeFileHandle h, uint code, byte[] inBuf, uint inSize,
        byte[] outBuf, uint outSize, out uint returned, IntPtr ov);

    const uint GENERIC_READ_WRITE = 0xC0000000;
    const uint OPEN_EXISTING = 3;
    const uint FILE_SHARE_READ_WRITE = 3;
    const uint IOCTL_GET_NODE_CONNECTION_INFORMATION_EX = 0x00220448;
    const uint IOCTL_USB_HUB_CYCLE_PORT = 0x00220444;

    public static string Query(string path, uint port) {
        using (var h = CreateFile(path, GENERIC_READ_WRITE,
                                  FILE_SHARE_READ_WRITE, IntPtr.Zero,
                                  OPEN_EXISTING, 0, IntPtr.Zero)) {
            if (h.IsInvalid)
                return "OPEN_ERR=" + Marshal.GetLastWin32Error();
            byte[] input = new byte[64];
            BitConverter.GetBytes(port).CopyTo(input, 0);
            byte[] output = new byte[4096];
            uint returned;
            bool ok = DeviceIoControl(
                h, IOCTL_GET_NODE_CONNECTION_INFORMATION_EX,
                input, (uint)input.Length, output, (uint)output.Length,
                out returned, IntPtr.Zero);
            if (!ok)
                return "QUERY_ERR=" + Marshal.GetLastWin32Error();
            ushort vid = BitConverter.ToUInt16(output, 12);
            ushort pid = BitConverter.ToUInt16(output, 14);
            ushort addr = BitConverter.ToUInt16(output, 25);
            uint status = BitConverter.ToUInt32(output, 31);
            return String.Format(
                "OK returned={0} vid=0x{1:X4} pid=0x{2:X4} addr={3} status={4}",
                returned, vid, pid, addr, status);
        }
    }

    public static string CyclePort(string path, uint port) {
        using (var h = CreateFile(path, GENERIC_READ_WRITE,
                                  FILE_SHARE_READ_WRITE, IntPtr.Zero,
                                  OPEN_EXISTING, 0, IntPtr.Zero)) {
            if (h.IsInvalid)
                return "OPEN_ERR=" + Marshal.GetLastWin32Error();
            byte[] input = new byte[8];
            BitConverter.GetBytes(port).CopyTo(input, 0);
            byte[] output = new byte[8];
            uint returned;
            // The documented IOCTL has no output buffer.  Try that first,
            // then fall back to the two-field USB_CYCLE_PORT_PARAMS form
            // used by some hub drivers.
            bool ok = DeviceIoControl(
                h, IOCTL_USB_HUB_CYCLE_PORT,
                input, (uint)input.Length, null, 0,
                out returned, IntPtr.Zero);
            if (!ok) {
                int err = Marshal.GetLastWin32Error();
                ok = DeviceIoControl(
                    h, IOCTL_USB_HUB_CYCLE_PORT,
                    input, (uint)input.Length, output, (uint)output.Length,
                    out returned, IntPtr.Zero);
                if (!ok)
                    return "CYCLE_ERR=" + Marshal.GetLastWin32Error() +
                           " first_err=" + err;
            }
            uint status = BitConverter.ToUInt32(output, 4);
            return String.Format(
                "OK returned={0} status_returned={1}", returned, status);
        }
    }
}
'@

if (-not ("UsbHubPort" -as [type])) {
    Add-Type -TypeDefinition $source
}

function Write-Log([string]$line) {
    $line | Out-File -Encoding utf8 -Append $LogPath
    Write-Output $line
}

if (Test-Path $LogPath) {
    Remove-Item -LiteralPath $LogPath
}
"schema=samurai-windows-usb-port-cycle-v1" | Out-File -Encoding utf8 $LogPath
Write-Log ("start={0} instance={1} requested_port={2}" -f (Get-Date -Format o), $InstanceId, $Port)

$phone = Get-PnpDevice -PresentOnly |
    Where-Object { $_.InstanceId -eq $InstanceId } |
    Select-Object -First 1
if (-not $phone) {
    throw "phone instance not present: $InstanceId"
}

$parent = (Get-PnpDeviceProperty -InstanceId $InstanceId `
    -KeyName "DEVPKEY_Device_Parent").Data
$location = (Get-PnpDeviceProperty -InstanceId $InstanceId `
    -KeyName "DEVPKEY_Device_LocationInfo").Data
if (-not $parent -or $parent -notlike "USB\ROOT_HUB30*") {
    throw "phone parent is not a USB root hub: $parent"
}
if ($Port -eq 0) {
    if ($location -notmatch "Port_#([0-9]+)") {
        throw "cannot parse port from LocationInfo: $location"
    }
    $Port = [int]$Matches[1]
}

$hubPath = "\\?\" + ($parent -replace "\\", "#") +
    "#{f18a0e88-c30c-11d0-8815-00a0c906bed8}"
Write-Log ("parent={0}" -f $parent)
Write-Log ("location={0}" -f $location)
Write-Log ("hub_path={0}" -f $hubPath)
Write-Log ("port={0}" -f $Port)

$before = [UsbHubPort]::Query($hubPath, [uint32]$Port)
Write-Log ("before={0}" -f $before)
if ($before -notmatch "vid=0x0525 pid=0xA4A1") {
    throw "port $Port is not the phone (expected 0525:a4a1): $before"
}

if ($QueryOnly -or -not $Cycle) {
    Write-Log "result=query-only"
    exit 0
}

Write-Log ("cycle_begin={0}" -f (Get-Date -Format o))
$cycleResult = [UsbHubPort]::CyclePort($hubPath, [uint32]$Port)
Write-Log ("cycle={0}" -f $cycleResult)
Write-Log ("cycle_end={0}" -f (Get-Date -Format o))

for ($i = 0; $i -lt 20; $i++) {
    Start-Sleep -Seconds 1
    $after = [UsbHubPort]::Query($hubPath, [uint32]$Port)
    Write-Log ("after[{0}]={1}" -f ($i + 1), $after)
    if ($after -match "vid=0x0525 pid=0xA4A1" -and $after -match "status=1") {
        break
    }
}

Write-Log ("result={0}" -f $(if ($cycleResult -like "OK*") { "cycle-issued" } else { "cycle-failed" }))
