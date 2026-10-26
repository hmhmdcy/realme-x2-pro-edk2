$ErrorActionPreference='Stop'
$out='E:/edk2-samurai-out/kernel171'
$prefix='speaker-sd1-first'
$fb='C:/Users/cy122/Downloads/platform-tools/platform-tools/fastboot.exe'
$serial=(Get-Content -Raw -LiteralPath 'E:/edk2-samurai-out/kernel109/fastboot-identity.json' | ConvertFrom-Json).serial
$build=Get-Content -Raw -LiteralPath "$out/build-package-validation.json" | ConvertFrom-Json
$q=Get-Content -Raw -LiteralPath "$out/quiesce-validation.json" | ConvertFrom-Json
$bootId=(Get-Content -Raw -LiteralPath "$out/source-boot-id-private.txt").Trim()
if ($serial -notmatch '^[a-z0-9]{8}$' -or $bootId -notmatch '^[a-f0-9-]{36}$') {throw 'Private identity guard missing'}
if (!$build.image_unchanged -or !$build.all_firmware_code_and_non_version_data_unchanged -or !$build.fat_readback_exact -or $build.kernel_build_kept -ne 168) {throw 'Candidate audit missing'}
if (!$q.quiesce_audit_pass -or $q.boot_id -ne $bootId -or !$q.all_remoteprocs_offline -or !$q.no_drm_userspace_clients -or !$q.gui_user_and_drm_crtcs_quiesced) {throw 'Current boot quiesce proof missing'}
if ((Get-Content -Raw -LiteralPath "$out/$prefix-freeze.out") -notmatch 'K171_F2FS_FROZEN_FOR_BOOTLOADER') {throw 'Freeze receipt missing'}
$events=Get-Content -LiteralPath "$out/$prefix-f1-wsl.events.jsonl" | ForEach-Object {$_ | ConvertFrom-Json}
if (@($events | Where-Object {$_.event -eq 'receipt' -and $_.text -eq 'F1'}).Count -ne 1 -or @($events | Where-Object {$_.event -eq 'out_submit'}).Count -ne 1) {throw 'Single F1 transition missing'}
$images=@{boot="$out/boot-partition-k171-speaker-sd1.img";logdump="$out/logdump-k171-speaker-sd1.img"}
foreach ($part in @('boot','logdump')) {
    $bytes=$build.($part+'_bytes');$digest=$build.($part+'_sha256')
    if ((Get-Item -LiteralPath $images[$part]).Length -ne $bytes -or (Get-FileHash -LiteralPath $images[$part]).Hash.ToLowerInvariant() -ne $digest) {throw 'Candidate bytes changed'}
}
function Invoke-Fastboot([string]$Name,[string[]]$Arguments) {
    $log="$out/$prefix-$Name-private.log"
    if (Test-Path -LiteralPath $log) {throw 'Fresh operation log required'}
    & $fb @Arguments *> $log
    if ($LASTEXITCODE -ne 0) {throw "Fastboot $Name failed; inspect state"}
    return (Get-Content -Raw -LiteralPath $log)
}
$devices=Invoke-Fastboot 'devices' @('devices')
if ($devices -notmatch ('(?im)^'+[regex]::Escape($serial)+'\s+fastboot\s*$')) {throw 'Fastboot identity mismatch'}
$product=Invoke-Fastboot 'product' @('-s',$serial,'getvar','product')
if ($product -notmatch 'product:\s*msmnile') {throw 'Unexpected product'}
foreach ($part in @('boot','logdump')) {
    $geometry=Invoke-Fastboot ('size-'+$part) @('-s',$serial,'getvar',('partition-size:'+$part))
    $pattern='partition-size:'+ $part + ':\s*(0x[0-9a-fA-F]+)'
    if ($geometry -notmatch $pattern -or [Convert]::ToInt64($Matches[1].Substring(2),16) -ne $build.($part+'_bytes')) {throw 'Partition geometry mismatch'}
}
foreach ($part in @('boot','logdump')) {
    $reply=Invoke-Fastboot ('flash-'+$part) @('-s',$serial,'flash',$part,$images[$part])
    if ($reply -notmatch ("Writing '"+$part+"'\s+OKAY") -or $reply -match 'FAILED') {throw 'Flash completion unconfirmed'}
}
$null=Invoke-Fastboot 'reboot' @('-s',$serial,'reboot')
[ordered]@{stage=171;flash_success=$true;kernel_build=168;partitions=@('boot','logdump');runtime_validation_pending=$true} | ConvertTo-Json | Set-Content -Encoding utf8NoBOM -LiteralPath "$out/flash-validation.json"
Write-Output 'K171_SPEAKER_SD1_FLASH_CONFIRMED_RUNTIME_PENDING'
