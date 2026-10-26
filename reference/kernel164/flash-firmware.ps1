param([ValidatePattern('^[a-z0-9-]+$')][string]$Prefix='firmware164')
$ErrorActionPreference='Stop'
$out='E:/edk2-samurai-out/kernel164'
$fb='C:/Users/cy122/Downloads/platform-tools/platform-tools/fastboot.exe'
$serial=(Get-Content -Raw -LiteralPath 'E:/edk2-samurai-out/kernel109/fastboot-identity.json' | ConvertFrom-Json).serial
$build=Get-Content -Raw -LiteralPath "$out/boot-package-validation.json" | ConvertFrom-Json
$q=Get-Content -Raw -LiteralPath "$out/quiesce-validation.json" | ConvertFrom-Json
$bootId=(Get-Content -Raw -LiteralPath "$out/source-boot-id-private.txt").Trim()
if (!$build.firmware_audit_pass -or !$build.only_bds_executable_changed -or !$build.pristine_all_modules_byte_exact_current132 -or !$build.boot_tail_preserved -or !$build.logdump163_kept -or !$build.embedded_dtb_unchanged_current132_and163) {throw 'Firmware audit absent'}
if (!$q.quiesce_audit_pass -or $q.boot_id -ne $bootId -or $q.current_kernel -ne 163 -or $q.target_kernel -ne 163 -or !$q.no_new_gpu_faults) {throw 'Fresh current163 state verification missing'}
if ((Get-Content -Raw -LiteralPath "$out/$Prefix-freeze.out") -notmatch 'K164_F2FS_FROZEN_FOR_BOOTLOADER') {throw 'Freeze receipt missing'}
$events=Get-Content -LiteralPath "$out/$Prefix-f1-wsl.events.jsonl" | ForEach-Object {$_ | ConvertFrom-Json}
if (@($events | Where-Object {$_.event -eq 'receipt' -and $_.text -eq 'F1'}).Count -ne 1 -or @($events | Where-Object {$_.event -eq 'out_submit'}).Count -ne 1) {throw 'Single F1 transition missing'}
$image="$out/boot-partition-k164-panel-handoff.img"
if ((Get-FileHash -LiteralPath $image).Hash.ToLowerInvariant() -ne $build.boot_sha256 -or (Get-Item -LiteralPath $image).Length -ne 100663296) {throw 'Candidate image mismatch'}
if ((Get-FileHash -LiteralPath "$out/boot-partition-before-private.img").Hash.ToLowerInvariant() -ne $build.current_backup_sha256) {throw 'Original backup hash mismatch'}
$enum=(& 'C:/Program Files/usbipd-win/usbipd.exe' list | Out-String)
if ($enum -notmatch '18d1:d00d\s+Android Bootloader Interface') {throw 'Actual bootloader USB unavailable'}
function Invoke-CurrentFastboot([string]$Name,[string[]]$Arguments) {
    $log="$out/$Prefix-$Name-private.log"
    if (Test-Path -LiteralPath $log) {throw 'Existing operation log; inspect state'}
    & $fb @Arguments *> $log
    if ($LASTEXITCODE -ne 0) {throw "Fastboot $Name failed; inspect state"}
    return (Get-Content -Raw -LiteralPath $log)
}
$devices=Invoke-CurrentFastboot 'devices' @('devices')
if ($devices -notmatch ('(?im)^'+[regex]::Escape($serial)+'\s+fastboot\s*$')) {throw 'Device identity mismatch'}
$product=Invoke-CurrentFastboot 'product' @('-s',$serial,'getvar','product')
if ($product -notmatch 'product:\s*msmnile') {throw 'Product mismatch'}
$geometry=Invoke-CurrentFastboot 'size-boot' @('-s',$serial,'getvar','partition-size:boot')
if ($geometry -notmatch 'partition-size:boot:\s*(0x[0-9a-fA-F]+)' -or [Convert]::ToInt64($Matches[1].Substring(2),16) -ne 100663296) {throw 'Boot geometry mismatch'}
$flash=Invoke-CurrentFastboot 'flash-boot' @('-s',$serial,'flash','boot',$image)
if ($flash -notmatch "Writing 'boot'\s+OKAY" -or $flash -match 'FAILED') {throw 'Write completion unconfirmed'}
$null=Invoke-CurrentFastboot 'reboot' @('-s',$serial,'reboot')
[ordered]@{stage=164;flash_success=$true;partitions=@('boot');kernel_build=163;runtime_validation_pending=$true} | ConvertTo-Json | Set-Content -LiteralPath "$out/flash-validation.json" -Encoding utf8NoBOM
Write-Output K164_FIRMWARE_BOOT_FLASH_CONFIRMED_KERNEL163_KEPT
