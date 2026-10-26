$ErrorActionPreference='Stop'
$out='E:\edk2-samurai-out\kernel73'
$proc=$null
try {
    $proc=Start-Process -FilePath 'C:\Users\cy122\Downloads\platform-tools\platform-tools\fastboot.exe' -ArgumentList @('-s','62bc28a1','reboot') -WindowStyle Hidden -PassThru -RedirectStandardOutput "$out\deps-reboot-fixed.out" -RedirectStandardError "$out\deps-reboot-fixed.err"
    if (!$proc.WaitForExit(15000)) {throw 'Reboot timed out'}
    $proc.WaitForExit()
    if ($proc.ExitCode -ne 0) {throw 'Reboot failed'}
    Get-Content "$out\deps-reboot-fixed.err"
    [ordered]@{utc=[DateTime]::UtcNow.ToString('o');serial='62bc28a1';flashed_partitions=@('logdump');flash_success=$true;reboot_success=$true;reboot_command_corrected=$true;boot_written=$false;userdata_written=$false;gpt_written=$false} | ConvertTo-Json | Set-Content "$out\deps-flash-validation.json"
} finally {
    if ($proc) {
        if (!$proc.HasExited) {$proc.Kill();$proc.WaitForExit()}
        $proc.Dispose()
    }
}
