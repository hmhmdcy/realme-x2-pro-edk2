$ErrorActionPreference='Stop'
$out='E:/edk2-samurai-out/kernel130'
$old=(Get-Content -LiteralPath "$out/source-boot-id-private.txt" -Raw).Trim()
$deadline=[DateTime]::UtcNow.AddSeconds(240)
for($i=1;[DateTime]::UtcNow -lt $deadline;$i++) {
    $path="$out/warmboot-ssh-$i-private.txt"
    if(Test-Path -LiteralPath $path){throw 'Fresh warmboot observation required'}
    try {
        & "$PSScriptRoot/../kernel109/usb-ssh-pmos.ps1" -Command 'uname -v; cat /proc/sys/kernel/random/boot_id; cat /proc/sys/kernel/tainted; cat /proc/uptime' *> $path
        $lines=Get-Content -LiteralPath $path
        if($lines.Count -ge 4 -and $lines[0] -match '^#129 ' -and $lines[1] -match '^[a-f0-9-]{36}$' -and $lines[1] -ne $old) {
            [System.IO.File]::WriteAllText("$out/embedded-boot-id-private.txt",$lines[1]+"`n",[System.Text.UTF8Encoding]::new($false))
            [ordered]@{new_boot_observed=$true;kernel_build=129;attempt=$i;observed_at_utc=[DateTime]::UtcNow.ToString('o');startup_service_full_audit_pending=$true} | ConvertTo-Json | Set-Content -LiteralPath "$out/warmboot-ssh-validation.json" -Encoding utf8NoBOM
            Write-Output 'K130_NEW129_WARM_BOOT_NATIVE_SSH_RECOVERED'
            exit 0
        }
    } catch {Add-Content -LiteralPath $path -Value $_.Exception.Message}
    Start-Sleep -Seconds 5
}
Write-Output 'K130_WARM_BOOT_OBSERVATION_BOUND_EXPIRED_NO_AUTOMATIC_RESET'
exit 2
