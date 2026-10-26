param([Parameter(Mandatory)][ValidatePattern('^[a-z0-9-]+$')][string]$Prefix,
      [ValidatePattern('^[a-z0-9-]+$')][string]$BootCheckpoint='clean-reboot-1')
$ErrorActionPreference='Stop'
$out='E:\edk2-samurai-out\kernel112'
$eud='E:\eud-host\eudtool.exe'
if (Test-Path -LiteralPath "$out\$Prefix-reboot-host.txt") {throw 'Use a fresh prefix'}
$command='test "$(cat /proc/sys/kernel/tainted)" = 0 && test "$(cat /sys/class/remoteproc/remoteproc0/state)" = offline && sh /var/lib/samurai/k112-rpcd-ram-trial/reboot-radio-clean.sh {0} "$(cat /var/lib/samurai/k112-{1}/boot-id-private.txt)"' -f $Prefix,$BootCheckpoint
& "$PSScriptRoot\..\kernel109\usb-ssh-pmos.ps1" -Command $command *> "$out\$Prefix-reboot-host.txt"
Write-Output 'NORMAL_OPENRC_REBOOT_REQUESTED_WITH_RADIO_CLEANUP'
# Each reader releases its owner before another host-side COM setup runs.
& "$PSScriptRoot\read-early-eud.ps1" -Prefix "$Prefix-shutdown" *> "$out\$Prefix-shutdown-reader.txt"
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
& "$PSScriptRoot\read-early-eud.ps1" -Prefix "$Prefix-startup" *> "$out\$Prefix-startup-reader.txt"
Write-Output 'BOUNDED_SHUTDOWN_AND_STARTUP_CAPTURE_COMPLETE'
