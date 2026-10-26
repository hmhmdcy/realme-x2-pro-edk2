param([string]$Prefix='same158-second')
$ErrorActionPreference='Stop'
$out='E:/edk2-samurai-out/kernel159'
$fb='C:/Users/cy122/Downloads/platform-tools/platform-tools/fastboot.exe'
$serial=(Get-Content -Raw -LiteralPath 'E:/edk2-samurai-out/kernel109/fastboot-identity.json' | ConvertFrom-Json).serial
$quiesce=Get-Content -Raw -LiteralPath "$out/quiesce-validation.json" | ConvertFrom-Json
$source=(Get-Content -Raw -LiteralPath "$out/source-boot-id-private.txt").Trim()
if (!$quiesce.quiesce_audit_pass -or $quiesce.boot_id -ne $source -or $quiesce.current_kernel -ne 158) {throw 'Current158 quiesce proof absent'}
if ((Get-Content -Raw -LiteralPath "$out/$Prefix-freeze.out") -notmatch 'K159_F2FS_FROZEN_FOR_BOOTLOADER') {throw 'Fresh freeze proof absent'}
$events=Get-Content -LiteralPath "$out/$Prefix-f1-wsl.events.jsonl" | ForEach-Object {$_ | ConvertFrom-Json}
if (@($events | Where-Object {$_.event -eq 'receipt' -and $_.text -eq 'F1'}).Count -ne 1 -or @($events | Where-Object {$_.event -eq 'out_submit'}).Count -ne 1) {throw 'Single F1 proof absent'}
$enum=(& 'C:/Program Files/usbipd-win/usbipd.exe' list | Out-String)
if ($enum -notmatch '18d1:d00d\s+Android Bootloader Interface') {throw 'Actual bootloader USB unavailable'}
foreach ($step in @('devices','product','reboot')) {
    $log="$out/same158-$step-private.log"
    if (Test-Path -LiteralPath $log) {throw 'Existing operation log; inspect device before retrying'}
    if ($step -eq 'devices') {
        & $fb devices *> $log
        if ($LASTEXITCODE -ne 0 -or (Get-Content -Raw -LiteralPath $log) -notmatch ('(?im)^'+[regex]::Escape($serial)+'\s+fastboot\s*$')) {throw 'Actual device identity mismatch'}
    } elseif ($step -eq 'product') {
        & $fb -s $serial getvar product *> $log
        if ($LASTEXITCODE -ne 0 -or (Get-Content -Raw -LiteralPath $log) -notmatch 'product:\s*msmnile') {throw 'Product mismatch'}
    } else {
        & $fb -s $serial reboot *> $log
        if ($LASTEXITCODE -ne 0) {throw 'Reboot outcome needs inspection'}
    }
}
[ordered]@{stage=159;kernel_build=158;flash_performed=$false;reboot_acknowledged=$true;new_boot_verification_pending=$true} | ConvertTo-Json | Set-Content -LiteralPath "$out/reboot-validation.json" -Encoding utf8NoBOM
Write-Output K159_SAME158_REBOOT_ACKNOWLEDGED
