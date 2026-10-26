$ErrorActionPreference='Stop'
$out='E:/edk2-samurai-out/kernel141'
$deadline=[DateTime]::UtcNow.AddSeconds(240)
$attempt=0
while ([DateTime]::UtcNow -lt $deadline) {
    $attempt++
    $path="$out/startup-ssh-$attempt-private.txt"
    if (Test-Path -LiteralPath $path) {throw 'Fresh observation prefix required'}
    try {
        & "$PSScriptRoot/../kernel109/usb-ssh-pmos.ps1" -Command 'python3 /var/lib/samurai/k141-pre-reboot/check-new-boot.py' *> $path
        if ((Get-Content -Raw -LiteralPath $path) -match 'K141_NEW140_BOOT_CONFIRMED') {
            Write-Output 'K141_NEW140_SSH_RECOVERED_STARTUP_CAPTURE_READY'
            exit 0
        }
    } catch {Add-Content -LiteralPath $path -Value $_.Exception.Message}
    Start-Sleep -Seconds 3
}
Write-Output 'K141_NEW_BOOT_OBSERVATION_EXPIRED_INSPECT_STATE_WITHOUT_REBOOT_REPLAY'
exit 2
