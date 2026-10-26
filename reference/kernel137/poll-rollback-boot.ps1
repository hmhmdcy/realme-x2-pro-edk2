$ErrorActionPreference='Stop'
$out='E:/edk2-samurai-out/kernel137'
$deadline=[DateTime]::UtcNow.AddSeconds(240)
$attempt=0
while ([DateTime]::UtcNow -lt $deadline) {
    $attempt++
    $path="$out/rollback-ssh-$attempt-private.txt"
    if (Test-Path -LiteralPath $path) {throw 'Fresh SSH observation prefix required'}
    try {
        & "$PSScriptRoot/../kernel109/usb-ssh-pmos.ps1" -Command 'uname -v; cat /proc/sys/kernel/tainted; ls /dev/dri 2>/dev/null || true; pgrep -x phosh || true; pgrep -x phoc || true' *> $path
        if ((Get-Content -LiteralPath $path -Raw) -match '^#132 ') {
            Write-Output 'K137_STABLE132_ROLLBACK_SSH_RECOVERED_FULL_RUNTIME_PENDING'
            exit 0
        }
    } catch {Add-Content -LiteralPath $path -Value $_.Exception.Message}
    Start-Sleep -Seconds 5
}
Write-Output 'K137_SSH_OBSERVATION_EXPIRED_INSPECT_DEVICE_STATE'
exit 2
