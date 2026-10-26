$ErrorActionPreference='Stop'
$out='E:/edk2-samurai-out/kernel142'
$prefix='irq-first'
$fb='C:/Users/cy122/Downloads/platform-tools/platform-tools/fastboot.exe'
$serial=(Get-Content -Raw -LiteralPath 'E:/edk2-samurai-out/kernel109/fastboot-identity.json' | ConvertFrom-Json).serial
$build=Get-Content -Raw -LiteralPath "$out/current140-build-package-validation.json" | ConvertFrom-Json
$recorder=Get-Content -Raw -LiteralPath "$out/early-recorder-install-validation.json" | ConvertFrom-Json
if (!$recorder.installed_recorder_three_files_exact -or !$recorder.one_new_boot_only) {throw 'Early recorder installation proof absent'}
$q=Get-Content -Raw -LiteralPath "$out/quiesce-validation.json" | ConvertFrom-Json
$bootId=(Get-Content -Raw -LiteralPath "$out/source-boot-id-private.txt").Trim()
if ($serial -notmatch '^[a-z0-9]{8}$' -or $bootId -notmatch '^[a-f0-9-]{36}$') {throw 'Private identity guard absent'}
if (!$build.same_current140_kernel_reboot_only -or !$build.four_artifacts_fresh_hash_verified -or !$q.quiesce_audit_pass -or $q.boot_id -ne $bootId) {throw 'Same current140 pre-reboot guards absent'}
if ((Get-Content -Raw -LiteralPath "$out/$prefix-freeze.out") -notmatch 'K142_F2FS_FROZEN_FOR_BOOTLOADER') {throw 'Freeze receipt absent'}
$events=Get-Content -LiteralPath "$out/$prefix-f1-wsl.events.jsonl" | ForEach-Object {$_ | ConvertFrom-Json}
if (@($events | Where-Object {$_.event -eq 'receipt' -and $_.text -eq 'F1'}).Count -ne 1 -or @($events | Where-Object {$_.event -eq 'out_submit'}).Count -ne 1) {throw 'Single F1 receipt absent'}
function Invoke-Fastboot([string]$Name,[string[]]$Arguments) {
    $log="$out/$prefix-$Name-private.log"
    if (Test-Path -LiteralPath $log) {throw 'Fresh operation required'}
    & $fb @Arguments *> $log
    if ($LASTEXITCODE -ne 0) {throw "Fastboot $Name failed; inspect state"}
    return (Get-Content -Raw -LiteralPath $log)
}
$devices=Invoke-Fastboot 'devices' @('devices')
if ($devices -notmatch ('(?im)^'+[regex]::Escape($serial)+'\s+fastboot\s*$')) {throw 'Fastboot identity mismatch'}
$product=Invoke-Fastboot 'product' @('-s',$serial,'getvar','product')
if ($product -notmatch 'product:\s*msmnile') {throw 'Unexpected product'}
$null=Invoke-Fastboot 'reboot' @('-s',$serial,'reboot')
[ordered]@{stage=142;same_kernel_build=140;reboot_success=$true;partitions_written=@();userdata_bulk_flash_or_erase=$false;startup_capture_pending=$true;goal_complete=$false} | ConvertTo-Json | Set-Content -LiteralPath "$out/reboot-validation.json" -Encoding utf8NoBOM
Write-Output 'K142_SAME140_FASTBOOT_REBOOT_NO_PARTITIONS_WRITTEN'
