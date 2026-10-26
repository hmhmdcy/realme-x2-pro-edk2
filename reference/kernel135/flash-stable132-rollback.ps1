$ErrorActionPreference='Stop'
$out='E:\edk2-samurai-out\kernel135'
$stable='E:\edk2-samurai-out\kernel132'
$prefix='rollback132-first'
$fb='C:\Users\cy122\Downloads\platform-tools\platform-tools\fastboot.exe'
$serial=(Get-Content -Raw -LiteralPath 'E:\edk2-samurai-out\kernel109\fastboot-identity.json' | ConvertFrom-Json).serial
$failure=Get-Content -Raw -LiteralPath "$PSScriptRoot\failed-runtime-validation.json" | ConvertFrom-Json
$q=Get-Content -Raw -LiteralPath "$out\rollback-quiesce-validation.json" | ConvertFrom-Json
$bootId=(Get-Content -Raw -LiteralPath "$out\failed-boot-id-private.txt").Trim()
$bundle=Get-Content -Raw -LiteralPath "$PSScriptRoot\..\kernel132\complete-bundle-validation.json" | ConvertFrom-Json
if ($serial -notmatch '^[a-z0-9]{8}$' -or $bootId -notmatch '^[a-f0-9-]{36}$') {throw 'Private identity guard missing'}
if (!$failure.candidate_rejected -or !$failure.boot_logdump_readback_exact -or !$failure.live_dtb_all_nodes_and_properties_verified -or !$failure.gpt18_persist_and_11_sources_preserved -or $failure.taint -ne 512) {throw 'Failed variant proof incomplete'}
if (!$q.quiesce_audit_pass -or $q.boot_id -ne $bootId -or !$q.all_remoteprocs_offline -or !$q.no_drm_userspace_clients -or !$q.gui_user_and_drm_crtcs_quiesced -or $q.target_kernel -ne 132 -or $q.taint -ne 512) {throw 'Failed boot quiesce proof missing'}
if (!$bundle.matching_boot_logdump_rootfs_modules_complete -or $bundle.candidate_kernel -ne 132 -or $bundle.release -ne '7.3.0-rc6-rmx1931-samurai-k132+') {throw 'Stable132 bundle proof missing'}
foreach ($item in @(@("$stable\boot-partition-k132-charger.img",'501074e6feb3c5e93eff86f40848acbfc102da44e06cf52f95770d80a83d07f6'),@("$stable\logdump-k132-charger.img",'db6b966975b987cd51e91f9488185b0a5e4a557755cc3b7043f0e6550aa19751'),@("$stable\modules-k132-private.tar.gz",'92e03906e3f437880590417070640bb0e81fada4638ab2a6dcaf8f57bbae923c'))) {
    if ((Get-FileHash -LiteralPath $item[0]).Hash.ToLowerInvariant() -ne $item[1]) {throw 'Stable rollback bytes changed'}
}
if ((Get-Content -Raw -LiteralPath "$out\$prefix-freeze.out") -notmatch 'K135_F2FS_FROZEN_FOR_BOOTLOADER') {throw 'Rollback freeze receipt missing'}
$events=Get-Content -LiteralPath "$out\$prefix-f1-wsl.events.jsonl" | ForEach-Object {$_ | ConvertFrom-Json}
if (@($events | Where-Object {$_.event -eq 'receipt' -and $_.text -eq 'F1'}).Count -ne 1 -or @($events | Where-Object {$_.event -eq 'out_submit'}).Count -ne 1) {throw 'Single rollback F1 transition missing'}
function Invoke-Fastboot([string]$Name,[string[]]$Arguments) {
    $log="$out\$prefix-$Name-private.log"
    if (Test-Path -LiteralPath $log) {throw 'Fresh rollback operation log required'}
    & $fb @Arguments *> $log
    if ($LASTEXITCODE -ne 0) {throw "Rollback fastboot $Name failed; inspect state"}
    return (Get-Content -Raw -LiteralPath $log)
}
$devices=Invoke-Fastboot 'devices' @('devices')
if ($devices -notmatch ('(?im)^'+[regex]::Escape($serial)+'\s+fastboot\s*$')) {throw 'Rollback fastboot identity mismatch'}
$product=Invoke-Fastboot 'product' @('-s',$serial,'getvar','product')
if ($product -notmatch 'product:\s*msmnile') {throw 'Unexpected product'}
foreach ($item in @(@('boot',[int64]100663296),@('logdump',[int64]67108864))) {
    $name=$item[0]
    $text=Invoke-Fastboot "size-$name" @('-s',$serial,'getvar',"partition-size:$name")
    if ($text -notmatch ("partition-size:$name"+':\s*(0x[0-9a-fA-F]+)') -or [Convert]::ToInt64($Matches[1].Substring(2),16) -ne $item[1]) {throw 'Rollback partition geometry mismatch'}
}
foreach ($item in @(@('boot',"$stable\boot-partition-k132-charger.img",[int64]100663296),@('logdump',"$stable\logdump-k132-charger.img",[int64]67108864))) {
    $partition=$item[0]
    if ((Get-Item -LiteralPath $item[1]).Length -ne $item[2]) {throw 'Stable image length mismatch'}
    $text=Invoke-Fastboot "flash-$partition" @('-s',$serial,'flash',$partition,$item[1])
    if ($text -notmatch ("Writing '"+$partition+"'\s+OKAY") -or $text -match 'FAILED') {throw 'Rollback flash completion unconfirmed'}
    Write-Output "K135_ROLLBACK132_FLASH_${partition}_CONFIRMED"
}
$null=Invoke-Fastboot 'reboot' @('-s',$serial,'reboot')
[ordered]@{flash_success=$true;rollback_target=132;failed_dt_variant=135;partitions=@('boot','logdump');userdata_bulk_flash_or_erase=$false;single_f1_transition_verified=$true;runtime_validation_pending=$true;goal_complete=$false} | ConvertTo-Json | Set-Content -Encoding utf8NoBOM -LiteralPath "$out\rollback-flash-validation.json"
Write-Output 'K135_STABLE132_ROLLBACK_FLASH_COMPLETE_RUNTIME_PENDING'
