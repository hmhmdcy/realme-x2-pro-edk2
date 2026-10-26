param(
    [Parameter(Mandatory=$true)][string]$OutputDirectory,
    [ValidateRange(30,180)][int]$DurationSeconds=100,
    [ValidateRange(100,1000)][int]$IntervalMs=200
)
# Host-only watchdog: bounds even initial PnP discovery/compilation. The child
# performs only reads. Terminating this owned process tree is not USB reset.
$ErrorActionPreference='Stop'
if (-not [System.IO.Path]::IsPathRooted($OutputDirectory) -or $OutputDirectory.Contains('"') -or $OutputDirectory.Contains("`n") -or $OutputDirectory.Contains("`r")) {
    throw 'Explicit absolute private output directory with no quote/newline required'
}
if ($PSVersionTable.PSVersion.Major -lt 7) { throw 'Run this watchdog with pwsh 7 (owned process-tree termination support)' }
$hostCaptureOut=[System.IO.Path]::GetFullPath($OutputDirectory)
$hostCaptureStdout=$hostCaptureOut+'.stdout-private.txt'
$hostCaptureStderr=$hostCaptureOut+'.stderr-private.txt'
$hostCaptureReceipt=$hostCaptureOut+'.watchdog.json'
foreach ($hostCapturePath in @($hostCaptureOut,$hostCaptureStdout,$hostCaptureStderr,$hostCaptureReceipt)) {
    if (Test-Path -LiteralPath $hostCapturePath) { throw 'New capture path only; do not overwrite or relaunch an old worker' }
}
if (-not (Test-Path -LiteralPath ([System.IO.Path]::GetDirectoryName($hostCaptureOut)) -PathType Container)) { throw 'Private parent directory must already exist' }
$hostCaptureExe=(Get-Command pwsh.exe -ErrorAction Stop).Source
$hostCaptureScript=Join-Path $PSScriptRoot 'watch-one-hub.ps1'
$hostCaptureArgs=@('-NoProfile','-NonInteractive','-File',('"'+$hostCaptureScript+'"'),'-OutputDirectory',('"'+$hostCaptureOut+'"'),
    '-DurationSeconds',$DurationSeconds,'-IntervalMs',$IntervalMs)
$hostCaptureStart=[DateTimeOffset]::UtcNow.ToString('o')
$hostCaptureProcess=Start-Process -FilePath $hostCaptureExe -ArgumentList $hostCaptureArgs -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput $hostCaptureStdout -RedirectStandardError $hostCaptureStderr
$hostCaptureTimer=[System.Diagnostics.Stopwatch]::StartNew()
$hostCaptureKilled=$false
try {
    while (-not $hostCaptureProcess.WaitForExit(500)) {
        if ($hostCaptureTimer.Elapsed.TotalSeconds -ge $DurationSeconds+20) {
            # This Process object still owns the child process handle. Kill
            # only this reader tree; no PnP/USB operation or device is targeted.
            $hostCaptureProcess.Kill($true)
            $hostCaptureKilled=$true
            break
        }
    }
    $hostCaptureExited=$hostCaptureProcess.WaitForExit(3000)
    $hostCaptureResult=[ordered]@{
        HostReaderOnly=$true; DeviceTrialExecuted=$false; Pid=$hostCaptureProcess.Id
        StartUtc=$hostCaptureStart; EndUtc=[DateTimeOffset]::UtcNow.ToString('o')
        HardDeadlineSeconds=$DurationSeconds+20; WatchdogTerminatedReader=$hostCaptureKilled
        WorkerExited=$hostCaptureExited; ExitCode=$(if ($hostCaptureExited) {$hostCaptureProcess.ExitCode} else {$null})
        OutputDirectory=$hostCaptureOut; CompleteCapture=($hostCaptureExited -and $hostCaptureProcess.ExitCode -eq 0 -and -not $hostCaptureKilled -and (Test-Path -LiteralPath (Join-Path $hostCaptureOut 'summary.json')))
    }
    $hostCaptureResult | ConvertTo-Json | Set-Content -LiteralPath $hostCaptureReceipt -Encoding utf8
    $hostCaptureResult | ConvertTo-Json
} finally {
    $hostCaptureProcess.Dispose()
}
