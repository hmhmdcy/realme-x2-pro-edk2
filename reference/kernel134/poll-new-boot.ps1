$ErrorActionPreference='Stop'
$out='E:\edk2-samurai-out\kernel134'
$deadline=[DateTime]::UtcNow.AddSeconds(240)
$attempt=0
while ([DateTime]::UtcNow -lt $deadline) {
    $attempt++
    $path="$out\postflash-ssh-$attempt-private.txt"
    if (Test-Path -LiteralPath $path) {throw 'Fresh SSH observation prefix required'}
    try {
        & "$PSScriptRoot\..\kernel109\usb-ssh-pmos.ps1" -Command 'uname -v; cat /proc/sys/kernel/tainted; ls /dev/dri 2>/dev/null || true; pgrep -x phosh || true; pgrep -x phoc || true' *> $path
        if ((Get-Content -LiteralPath $path -Raw) -match '^#134 ') {
            [ordered]@{ssh_recovered=$true;kernel_build=134;attempt=$attempt;observed_at_utc=[DateTime]::UtcNow.ToString('o');full_runtime_audit_pending=$true} | ConvertTo-Json | Set-Content -LiteralPath "$out\ssh-recovery-validation.json" -Encoding utf8NoBOM
            Write-Output 'K134_NATIVE_SSH_RECOVERED_RUNTIME_AUDIT_PENDING'
            exit 0
        }
    } catch {Add-Content -LiteralPath $path -Value $_.Exception.Message}
    Start-Sleep -Seconds 5
}
Write-Output 'K134_SSH_OBSERVATION_BOUND_EXPIRED_INSPECT_DEVICE_STATE_NO_AUTOMATIC_RESET'
exit 2

