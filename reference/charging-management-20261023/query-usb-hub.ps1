# Read-only Windows USB hub/port queries, using Windows SDK 10.0.26100 layouts.
# No reset, cycle-port, power, install, detach, or device restart operation.
$ErrorActionPreference = 'Stop'
$chargingHubDevices = @(Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -like 'USB\VID_05C6&PID_9500\*' })
if ($chargingHubDevices.Count -ne 1) { throw 'Expected exactly one present EUD hub' }
$chargingInterfaceText = (& pnputil /enum-devices /instanceid $chargingHubDevices[0].InstanceId /interfaces | Out-String)
if ($LASTEXITCODE -ne 0) { throw 'Read-only interface query failed' }
$chargingHubMatches = [regex]::Matches($chargingInterfaceText, '\\\\\?\\USB#VID_05C6&PID_9500#[^\r\n ]+#\{f18a0e88-c30c-11d0-8815-00a0c906bed8\}', 'IgnoreCase')
if ($chargingHubMatches.Count -ne 1) { throw 'Expected one observed EUD hub interface' }
$chargingHubPath = $chargingHubMatches[0].Value
Add-Type -TypeDefinition @'
using System;
using System.ComponentModel;
using System.Runtime.InteropServices;
using Microsoft.Win32.SafeHandles;
public static class ChargingUsbHubRead {
  [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
  static extern SafeFileHandle CreateFile(string path, uint access, uint share,
    IntPtr security, uint disposition, uint flags, IntPtr template);
  [DllImport("kernel32.dll", SetLastError=true)]
  static extern bool DeviceIoControl(SafeFileHandle handle, uint ioctl,
    byte[] input, uint inputLength, byte[] output, uint outputLength,
    out uint returned, IntPtr overlapped);
  public static byte[] Query(string path, uint ioctl, byte[] buffer) {
    if (ioctl != 0x220408 && ioctl != 0x220448)
      throw new ArgumentException("Only GET_NODE_INFORMATION/GET_CONNECTION_INFORMATION_EX allowed");
    using (var handle=CreateFile(path, 0, 3, IntPtr.Zero, 3, 0x80, IntPtr.Zero)) {
      if (handle.IsInvalid) throw new Win32Exception(Marshal.GetLastWin32Error());
      uint count;
      if (!DeviceIoControl(handle, ioctl, buffer, (uint)buffer.Length,
          buffer, (uint)buffer.Length, out count, IntPtr.Zero))
        throw new Win32Exception(Marshal.GetLastWin32Error());
      if (count < (ioctl == 0x220408 ? 76 : 35) || count > buffer.Length)
        throw new InvalidOperationException("Invalid query response size");
      Array.Resize(ref buffer, (int)count);
      return buffer;
    }
  }
}
'@
$chargingNode = [ChargingUsbHubRead]::Query($chargingHubPath, 0x220408, [byte[]]::new(76))
if ($chargingNode[5] -ne 0x29 -or $chargingNode[6] -lt 1 -or $chargingNode[6] -gt 15 -or $chargingNode[75] -gt 1) {
    throw 'Unexpected hub descriptor; refuse to decode guessed offsets'
}
$chargingPortStates = @()
for ($chargingPort = 1; $chargingPort -le $chargingNode[6]; $chargingPort++) {
    $chargingBuffer = [byte[]]::new(512)
    [BitConverter]::GetBytes([uint32]$chargingPort).CopyTo($chargingBuffer, 0)
    $chargingData = [ChargingUsbHubRead]::Query($chargingHubPath, 0x220448, $chargingBuffer)
    # usbioctl.h user-mode structures are under pshpack1.h, not default packing.
    $chargingPortStates += [pscustomobject]@{
        Port = $chargingPort
        Status = [BitConverter]::ToUInt32($chargingData, 31)
        Vendor = ('{0:x4}' -f [BitConverter]::ToUInt16($chargingData, 12))
        Product = ('{0:x4}' -f [BitConverter]::ToUInt16($chargingData, 14))
        Configuration = $chargingData[22]
        Speed = $chargingData[23]
        IsHub = [bool]$chargingData[24]
    }
}
$chargingResult = [pscustomobject]@{
    ReadOnly = $true
    Interface = $chargingHubPath
    PortCount = $chargingNode[6]
    HubIsBusPowered = [bool]$chargingNode[75]
    HubControllerCurrentMa = $chargingNode[10]
    Ports = $chargingPortStates
    WindowsSdk = '10.0.26100.0'
}
$chargingOut = 'E:/edk2-samurai-out/charging-management-20261023/host-usb-topology'
New-Item -ItemType Directory -Path $chargingOut -Force | Out-Null
$chargingResult | ConvertTo-Json -Depth 7 | Set-Content -LiteralPath "$chargingOut/eud-hub-private.json"
$chargingResult | Select-Object ReadOnly,PortCount,HubIsBusPowered,HubControllerCurrentMa,Ports | ConvertTo-Json -Depth 7
