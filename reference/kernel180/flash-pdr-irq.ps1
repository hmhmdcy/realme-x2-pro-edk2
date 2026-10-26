$ErrorActionPreference='Stop'
$out='E:/edk2-samurai-out/kernel180'
$prefix='port-first'
$fb='C:/Users/cy122/Downloads/platform-tools/platform-tools/fastboot.exe'
$serial=(Get-Content -Raw -LiteralPath 'E:/edk2-samurai-out/kernel109/fastboot-identity.json' | ConvertFrom-Json).serial
$build=Get-Content -Raw -LiteralPath "$out/build-package-validation.json" | ConvertFrom-Json
$q=Get-Content -Raw -LiteralPath "$out/quiesce-validation.json" | ConvertFrom-Json
$bootId=(Get-Content -Raw -LiteralPath "$out/source-boot-id-private.txt").Trim()
if (!$build.pdr_transaction_peer_and_lifetime_fix_included -or !$build.dtb172_unchanged -or !$build.fat_readback_exact -or !$build.modules132_runtime_compatible -or $build.kernel_build -ne 180) {throw 'Candidate audit missing'}
if (!$q.quiesce_audit_pass -or $q.boot_id -ne $bootId -or !$q.all_remoteprocs_offline -or !$q.no_drm_userspace_clients -or $q.taint -ne 0) {throw 'Current clean boot quiesce proof missing'}
if ((Get-Content -Raw -LiteralPath "$out/$prefix-freeze.out") -notmatch 'K180_F2FS_FROZEN_FOR_BOOTLOADER') {throw 'Freeze receipt missing'}
$transition=Get-Content -Raw -LiteralPath "$out/restart2-transition-validation.json" | ConvertFrom-Json
if (!$transition.fresh_fastboot_observed -or !$transition.pre_restart_linux_inspection_pass -or $transition.standard_restart2_request_count -ne 1 -or $transition.restart2_command -ne 'bootloader') {throw 'Current bootloader transition evidence missing'}
$image="$out/logdump-k180-pdr-irq.img"
if ((Get-Item -LiteralPath $image).Length -ne $build.logdump_bytes -or (Get-FileHash -LiteralPath $image).Hash.ToLowerInvariant() -ne $build.logdump_sha256) {throw 'Candidate bytes changed'}
function Invoke-Fastboot([string]$Name,[string[]]$Arguments) {
 $log="$out/$prefix-$Name-private.log"
 if (Test-Path -LiteralPath $log) {throw 'Fresh operation required'}
 & $fb @Arguments *> $log
 if ($LASTEXITCODE -ne 0) {throw "Fastboot $Name failed; inspect state"}
 return Get-Content -Raw -LiteralPath $log
}
$devices=Invoke-Fastboot 'devices' @('devices')
if ($devices -notmatch ('(?im)^'+[regex]::Escape($serial)+'\s+fastboot\s*$')) {throw 'Current fastboot identity mismatch'}
$product=Invoke-Fastboot 'product' @('-s',$serial,'getvar','product')
if ($product -notmatch 'product:\s*msmnile') {throw 'Unexpected product'}
$geometry=Invoke-Fastboot 'size-logdump' @('-s',$serial,'getvar','partition-size:logdump')
if ($geometry -notmatch 'partition-size:logdump:\s*(0x[0-9a-fA-F]+)' -or [Convert]::ToInt64($Matches[1].Substring(2),16) -ne $build.logdump_bytes) {throw 'Partition geometry mismatch'}
$reply=Invoke-Fastboot 'flash-logdump' @('-s',$serial,'flash','logdump',$image)
if ($reply -notmatch "Writing 'logdump'\s+OKAY" -or $reply -match 'FAILED') {throw 'Flash completion unconfirmed'}
$null=Invoke-Fastboot 'reboot' @('-s',$serial,'reboot')
[ordered]@{stage=180;flash_success=$true;kernel_build=180;partitions=@('logdump');firmware172_retained=$true;runtime_validation_pending=$true} | ConvertTo-Json | Set-Content -Encoding utf8NoBOM -LiteralPath "$out/flash-validation.json"
Write-Output 'K180_LOGDUMP_FLASH_CONFIRMED_RUNTIME_PENDING'
