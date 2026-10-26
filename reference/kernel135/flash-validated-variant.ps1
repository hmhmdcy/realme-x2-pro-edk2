param([ValidatePattern('^[a-z0-9-]+$')][string]$Prefix='mdss-reset-first')
$ErrorActionPreference='Stop'
$out='E:\edk2-samurai-out\kernel135'
$fb='C:\Users\cy122\Downloads\platform-tools\platform-tools\fastboot.exe'
$serial=(Get-Content -LiteralPath 'E:\edk2-samurai-out\kernel109\fastboot-identity.json' -Raw | ConvertFrom-Json).serial
if ($serial -notmatch '^[a-z0-9]{8}$') {throw 'Device identity guard missing'}
$dt=Get-Content -Raw -LiteralPath "$PSScriptRoot\dtb-validation.json" | ConvertFrom-Json
$boot=Get-Content -Raw -LiteralPath "$out\boot-package-validation.json" | ConvertFrom-Json
$before=Get-Content -Raw -LiteralPath "$out\preflash-validation.json" | ConvertFrom-Json
$q=Get-Content -Raw -LiteralPath "$out\quiesce-validation.json" | ConvertFrom-Json
$bootId=(Get-Content -Raw -LiteralPath "$out\source-boot-id-private.txt").Trim()
if (!$dt.exactly_one_property_added -or !$dt.reset_provider_hardware_map_verified -or $dt.reset_index -ne 0 -or $dt.software_generation -ne 134 -or $dt.stage -ne 135 -or $dt.new_schema_diagnostics -ne 0) {throw 'MDSS reset DT contract incomplete'}
if (!$boot.only_embedded_dtb_changed -or !$boot.other_uefi_executable_bytes_unchanged -or !$boot.fat_readback_exact -or !$boot.fat_readonly_check_pass -or !$boot.fat_and_embedded_dtb_exactly_match_candidate -or $boot.dtb_sha256 -ne $dt.dtb_sha256 -or ($boot.flash_partitions -join ',') -ne 'boot,logdump') {throw 'Candidate package scope rejected'}
if (!$before.preflash_audit_pass -or $before.current_kernel -ne 134 -or $before.dt_variant -ne 135 -or $before.boot_id -ne $bootId -or !$before.gpt18_unchanged -or !$before.nv6_source4_vendor1_preserved -or !$before.persist_unchanged -or !$before.live_backups_match) {throw 'Fresh current134 rollback proof missing'}
if (!$q.quiesce_audit_pass -or $q.boot_id -ne $bootId -or !$q.gui_user_and_drm_crtcs_quiesced -or !$q.no_drm_userspace_clients -or !$q.all_remoteprocs_offline -or !$q.reused134_module_checks_pass -or $q.drm_minor -ne 0) {throw 'Current134 quiesce proof missing'}
foreach ($item in @(@("$out\boot-partition-before-private.img",$before.before_boot_sha256),@("$out\logdump-before-private.img",$before.before_logdump_sha256),@("$out\boot-partition-k135-mdss-reset.img",$boot.boot_sha256),@("$out\logdump-k135-mdss-reset.img",$boot.logdump_sha256),@("$out\DTB-k135-private",$dt.dtb_sha256),@('E:\edk2-samurai-out\kernel134\Image-k134-private','c4ec417d5f92cd3625b5109c38417b9eed95abafc1514c27196afd8d1dd98c97'),@('E:\edk2-samurai-out\kernel134\modules-k134-private.tar.gz','7945801ace5de6243d160914057da99418cdff9fc8cea98d8196518f01db2b1e'))) {
    if ((Get-FileHash -LiteralPath $item[0]).Hash.ToLowerInvariant() -ne $item[1]) {throw 'Candidate or rollback bytes changed'}
}
if ((Get-Content -Raw -LiteralPath "$out\$Prefix-freeze.out") -notmatch 'K135_F2FS_FROZEN_FOR_BOOTLOADER') {throw 'Freeze receipt missing'}
$events=Get-Content -LiteralPath "$out\$Prefix-f1-wsl.events.jsonl" | ForEach-Object {$_ | ConvertFrom-Json}
if (@($events | Where-Object {$_.event -eq 'receipt' -and $_.text -eq 'F1'}).Count -ne 1 -or @($events | Where-Object {$_.event -eq 'out_submit'}).Count -ne 1) {throw 'Single F1 transition proof missing'}
function Invoke-Fastboot([string]$Name,[string[]]$Arguments) {
    $log="$out\$Prefix-$Name-private.log"
    if (Test-Path -LiteralPath $log) {throw 'Fresh operation log required'}
    & $fb @Arguments *> $log
    if ($LASTEXITCODE -ne 0) {throw "Fastboot $Name failed; inspect state before further actions"}
    return (Get-Content -Raw -LiteralPath $log)
}
$usb=& 'C:\Program Files\usbipd-win\usbipd.exe' list | Out-String
if ($usb -match '(?m)^6-5\s+05c6:9505\s+[^\r\n]*Attached') {throw 'EUD still attached'}
$devices=Invoke-Fastboot 'devices' @('devices')
if ($devices -notmatch ('(?im)^'+[regex]::Escape($serial)+'\s+fastboot\s*$')) {throw 'Fastboot identity mismatch'}
$product=Invoke-Fastboot 'product' @('-s',$serial,'getvar','product')
if ($product -notmatch 'product:\s*msmnile') {throw 'Unexpected product'}
foreach ($item in @(@('boot',[int64]100663296),@('logdump',[int64]67108864))) {
    $name=$item[0]
    $text=Invoke-Fastboot "size-$name" @('-s',$serial,'getvar',"partition-size:$name")
    if ($text -notmatch ("partition-size:$name"+':\s*(0x[0-9a-fA-F]+)') -or [Convert]::ToInt64($Matches[1].Substring(2),16) -ne $item[1]) {throw 'Partition geometry mismatch'}
}
foreach ($item in @(@('boot',"$out\boot-partition-k135-mdss-reset.img",[int64]100663296),@('logdump',"$out\logdump-k135-mdss-reset.img",[int64]67108864))) {
    $partition=$item[0]
    if ((Get-Item -LiteralPath $item[1]).Length -ne $item[2]) {throw 'Image length mismatch'}
    $text=Invoke-Fastboot "flash-$partition" @('-s',$serial,'flash',$partition,$item[1])
    if ($text -notmatch ("Writing '"+$partition+"'\s+OKAY") -or $text -match 'FAILED') {throw 'Flash completion unconfirmed'}
    Write-Output "K135_FLASH_${partition}_CONFIRMED"
}
$null=Invoke-Fastboot 'reboot' @('-s',$serial,'reboot')
[ordered]@{flash_success=$true;dt_variant=135;software_generation=134;release=$dt.release;partitions=@('boot','logdump');boot_sha256=$boot.boot_sha256;logdump_sha256=$boot.logdump_sha256;userdata_bulk_flash_or_erase=$false;root_frozen_before_reboot=$true;single_f1_transition_verified=$true;runtime_validation_pending=$true;goal_complete=$false} | ConvertTo-Json | Set-Content -Encoding utf8NoBOM -LiteralPath "$out\flash-validation.json"
Write-Output 'K135_DT_ONLY_BOOT_LOGDUMP_FLASH_COMPLETE_RUNTIME_PENDING'
