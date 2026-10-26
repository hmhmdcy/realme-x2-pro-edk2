# Qualcomm eud_msm_reset: assert CTLOUT bit0 low, wait, then release high.
# Source: E:/eud-host/quic-eud/src/ctl_api.cpp, eud_msm_reset().
# EUD remains powered across the MSM reset. No partition command is involved.
$ErrorActionPreference='Stop'
$taskOut='E:/edk2-samurai-out/kernel357'
$taskMarker="$taskOut/system-reset-r1-private.json"
if (Test-Path -LiteralPath $taskMarker) {throw 'Existing reset attempt: inspect its result instead of repeating it'}
$taskEvidence=Get-Content "$taskOut/passive-r2.txt" -Raw
if ($taskEvidence -notmatch "CPUS still haven't responded to the NMI: 5") {throw 'CPU-stall evidence absent'}
$taskUsb=Get-PnpDevice -PresentOnly | Where-Object {$_.InstanceId -like 'USB*' -and $_.FriendlyName -eq 'Qualcomm EUD Control Device 9501'}
if (@($taskUsb).Count -ne 1) {throw 'The observed EUD control endpoint is no longer unique/present'}
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using Microsoft.Win32.SafeHandles;
public static class SamuraiEudReset357 {
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)]
 public static extern SafeFileHandle CreateFile(string path,uint access,uint share,IntPtr security,uint creation,uint flags,IntPtr template);
 [DllImport("kernel32.dll",SetLastError=true)]
 public static extern bool WriteFile(SafeFileHandle h,byte[] data,uint count,out uint written,IntPtr overlapped);
}
'@
$taskHandle=[SamuraiEudReset357]::CreateFile('\\.\Qualcomm EUD Control Device 9501\DEBUG',[uint32]3221225472,3,[IntPtr]::Zero,3,0x80,[IntPtr]::Zero)
if ($taskHandle.IsInvalid) {throw 'Cannot open EUD control endpoint'}
$taskState=@{utc=(Get-Date).ToUniversalTime().ToString('o');assert_attempted=$false;assert_written=$false;release_attempted=$false;release_written=$false;reset_hold_ms=100;system_restart_observed=$false}
function Save-Reset357 { $taskState | ConvertTo-Json | Set-Content -LiteralPath $taskMarker -Encoding utf8NoBOM }
try {
    $taskState.assert_attempted=$true;Save-Reset357
    [uint32]$taskWritten=0
    $taskAccepted=[SamuraiEudReset357]::WriteFile($taskHandle,[byte[]]@(8,1,0,0,0),5,[ref]$taskWritten,[IntPtr]::Zero)
    $taskState.assert_written=$taskAccepted -and $taskWritten -eq 5;Save-Reset357
    if (!$taskState.assert_written) {throw 'EUD reset assertion completion uncertain'}
    Start-Sleep -Milliseconds 100
} finally {
    try {
        $taskState.release_attempted=$true;Save-Reset357
        [uint32]$taskReleased=0
        $taskAccepted=[SamuraiEudReset357]::WriteFile($taskHandle,[byte[]]@(7,1,0,0,0),5,[ref]$taskReleased,[IntPtr]::Zero)
        $taskState.release_written=$taskAccepted -and $taskReleased -eq 5;Save-Reset357
    } finally { $taskHandle.Dispose() }
}
if (!$taskState.release_written) {throw 'EUD reset release completion uncertain; inspect control state'}
$taskState | ConvertTo-Json
