param([Parameter(Mandatory)][ValidatePattern('^[a-z0-9-]+$')][string]$Prefix,
      [ValidatePattern('^[a-z0-9-]+$')][string]$BootCheckpoint='audio-radio-quiesce-5', [ValidateSet(0,512)][int]$ExpectedTaint=512)
$ErrorActionPreference='Stop'
$out='E:\edk2-samurai-out\kernel113'
$eud='E:\eud-host\eudtool.exe'
if (Test-Path -LiteralPath "$out\$Prefix-reboot-host.txt") {throw 'Use a fresh prefix'}
$command='set -eu; uname -v | grep -q "^#113 "; test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k113-{1}/boot-id-private.txt)"; test "$(cat /proc/sys/kernel/tainted)" = {2}; test "$(cat /sys/devices/platform/sensor-power/state)" = "vdd=0 vddio=0"; for number in 0 1 2; do test "$(cat /sys/class/remoteproc/remoteproc$number/state)" = offline; done; test -z "$(pgrep -u 10000 || true)"; test -f /var/lib/samurai/k113-{1}/SHA256SUMS; sync; nohup /bin/sh -c "sleep 2; exec /sbin/reboot" > /run/k113-{0}-normal-reboot.log 2>&1 < /dev/null & echo AUDIO_QUIESCED_NORMAL_OPENRC_REBOOT_REQUESTED' -f $Prefix,$BootCheckpoint,$ExpectedTaint

& "$PSScriptRoot\..\kernel109\usb-ssh-pmos.ps1" -Command $command *> "$out\$Prefix-reboot-host.txt"
Write-Output 'NORMAL_OPENRC_REBOOT_REQUESTED_WITH_RADIO_CLEANUP'
# Each reader releases its owner before another host-side COM setup runs.
$shutdownComplete=$false
try {
    & "$PSScriptRoot\read-early-eud.ps1" -Prefix "$Prefix-shutdown" *> "$out\$Prefix-shutdown-reader.txt"
    $shutdownComplete=$true
} catch {
    Add-Content -LiteralPath "$out\$Prefix-shutdown-reader.txt" -Value $_.ToString()
    Write-Output 'SHUTDOWN_CAPTURE_INTERRUPTED_OWNER_RELEASED_CONTINUING_NEW_BOOT_CAPTURE'
}
$deadline=[DateTime]::UtcNow.AddSeconds(30)
$enabled=$false
$attempt=0
while ([DateTime]::UtcNow -lt $deadline -and !$enabled) {
    $attempt++
    $process=$null
    try {
        $process=Start-Process -FilePath $eud -ArgumentList @('com-up') -WindowStyle Hidden -PassThru -RedirectStandardOutput "$out\$Prefix-com-up-$attempt.out" -RedirectStandardError "$out\$Prefix-com-up-$attempt.err"
        if ($process.WaitForExit(4000)) {
            $process.WaitForExit()
            $enabled=($process.ExitCode -eq 0)
        }
    } finally {
        if ($process) {
            if (!$process.HasExited) {$process.Kill();$process.WaitForExit()}
            $process.Dispose()
        }
    }
    if (!$enabled) {Start-Sleep -Milliseconds 500}
}
if (!$enabled) {throw 'New-boot EUD COM setup unavailable within 30 seconds'}
Write-Output 'NEW_BOOT_COM_ENABLED'
$startupComplete=$false
try {
    & "$PSScriptRoot\read-early-eud.ps1" -Prefix "$Prefix-startup" *> "$out\$Prefix-startup-reader.txt"
    $startupComplete=$true
} catch {
    Add-Content -LiteralPath "$out\$Prefix-startup-reader.txt" -Value $_.ToString()
    Write-Output 'STARTUP_CAPTURE_INTERRUPTED_OWNER_RELEASED_REQUIRES_POSTBOOT_RECAPTURE'
}
@{shutdown_capture_complete=$shutdownComplete;startup_capture_complete=$startupComplete;
  postboot_recapture_required=(!$startupComplete);readers_released=$true} |
    ConvertTo-Json | Set-Content -LiteralPath "$out\$Prefix-capture-status-private.json"
Write-Output 'BOUNDED_SHUTDOWN_AND_STARTUP_CAPTURE_ATTEMPTS_FINISHED'
