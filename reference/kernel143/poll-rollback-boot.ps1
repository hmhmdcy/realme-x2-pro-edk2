$ErrorActionPreference='Stop'
$out='E:/edk2-samurai-out/kernel143'
$deadline=[DateTime]::UtcNow.AddSeconds(240)
$attempt=0
while ([DateTime]::UtcNow -lt $deadline) {
    $attempt++
    $path="$out/rollback-ssh-$attempt-private.txt"
    if (Test-Path -LiteralPath $path) {throw 'Fresh observation prefix required'}
    try {
        & "$PSScriptRoot/../kernel109/usb-ssh-pmos.ps1" -Command 'python3 /var/lib/samurai/k143-pre-reboot/check-rollback-boot.py' *> $path
        if ((Get-Content -Raw -LiteralPath $path) -match 'K143_RESTORED140_BOOT_CONFIRMED') {
            Write-Output 'K143_RESTORED140_SSH_RECOVERED_STARTUP_CAPTURE_READY'
            exit 0
        }
    } catch {Add-Content -LiteralPath $path -Value $_.Exception.Message}
    Start-Sleep -Seconds 3
}
Write-Output 'K143_NEW_BOOT_OBSERVATION_EXPIRED_INSPECT_STATE_WITHOUT_REBOOT_REPLAY'
exit 2
