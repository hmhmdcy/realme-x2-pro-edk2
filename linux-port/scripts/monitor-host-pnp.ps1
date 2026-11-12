param(
    [int]$DurationSeconds = 300,
    [int]$IntervalMilliseconds = 100,
    [string]$InstanceIdPattern = "USB\VID_0525&PID_A4A1*",
    [string]$LogPath = "host-pnp-heartbeat.txt"
)

$ErrorActionPreference = "Continue"

if ($IntervalMilliseconds -lt 50) {
    throw "IntervalMilliseconds must be at least 50"
}

$source = @'
using System;
using System.Runtime.InteropServices;

public static class DevNodeStatus {
    [DllImport("cfgmgr32.dll", CharSet = CharSet.Unicode)]
    private static extern uint CM_Locate_DevNodeW(
        out uint devInst, string deviceId, uint flags);

    [DllImport("cfgmgr32.dll")]
    private static extern uint CM_Get_DevNode_Status(
        out uint status, out uint problemNumber, uint devInst, uint flags);

    private const uint CM_LOCATE_DEVNODE_PHANTOM = 1;
    private const uint CR_SUCCESS = 0;
    private const uint DN_STATUS_PRESENT = 0x00000002;

    public static string Query(string deviceId) {
        uint devInst;
        uint rc = CM_Locate_DevNodeW(out devInst, deviceId, CM_LOCATE_DEVNODE_PHANTOM);
        if (rc != CR_SUCCESS)
            return String.Format("locate_rc={0} present=0 problem=unknown status=0", rc);

        uint status;
        uint problem;
        rc = CM_Get_DevNode_Status(out status, out problem, devInst, 0);
        if (rc != CR_SUCCESS)
            return String.Format("status_rc={0} present=0 problem=unknown status=0", rc);

        return String.Format(
            "locate_rc=0 status_rc=0 present={0} problem={1} status=0x{2:X8}",
            (status & DN_STATUS_PRESENT) != 0 ? 1 : 0, problem, status);
    }
}
'@

if (-not ("DevNodeStatus" -as [type])) {
    Add-Type -TypeDefinition $source
}

$devices = @(Get-PnpDevice -PresentOnly |
    Where-Object { $_.InstanceId -like $InstanceIdPattern } |
    Select-Object -ExpandProperty InstanceId -Unique)
if (-not $devices) {
    throw "no present device matches $InstanceIdPattern"
}

$writer = New-Object System.IO.StreamWriter($LogPath, $false)
$writer.AutoFlush = $true
$deadline = (Get-Date).AddSeconds($DurationSeconds)
$sample = 0
$presenceFailures = 0
$problemFailures = 0

$writer.WriteLine("schema=samurai-host-pnp-cfgmgr32-v1")
$startLine = "start={0} duration={1} interval_ms={2} devices={3}" -f `
    (Get-Date -Format o), $DurationSeconds, $IntervalMilliseconds, `
    ($devices -join ";")
$writer.WriteLine($startLine)

try {
    while ((Get-Date) -lt $deadline) {
        $sample++
        $allPresent = $true
        $allOk = $true
        $entries = @()

        foreach ($device in $devices) {
            $result = [DevNodeStatus]::Query($device)
            $entries += ("{0}[{1}]" -f $device, $result)
            if ($result -notmatch "present=1") {
                $allPresent = $false
            }
            if ($result -notmatch "present=1 problem=0 ") {
                $allOk = $false
            }
        }

        if (-not $allPresent) {
            $presenceFailures++
        } elseif (-not $allOk) {
            $problemFailures++
        }

        $sampleLine = "{0} sample={1} present={2} ok={3} {4}" -f `
            (Get-Date -Format o), $sample, $allPresent, $allOk, `
            ($entries -join " ")
        $writer.WriteLine($sampleLine)

        Start-Sleep -Milliseconds $IntervalMilliseconds
    }
} finally {
    $endLine = "end={0} samples={1} presence_failures={2} problem_failures={3}" -f `
        (Get-Date -Format o), $sample, $presenceFailures, $problemFailures
    $writer.WriteLine($endLine)
    $writer.Dispose()
}
