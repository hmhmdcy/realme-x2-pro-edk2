$ErrorActionPreference='Stop'
$out='E:/edk2-samurai-out/kernel143'
$prefix='rollback140-first'
$fb='C:/Users/cy122/Downloads/platform-tools/platform-tools/fastboot.exe'
$serial=(Get-Content -Raw -LiteralPath 'E:/edk2-samurai-out/kernel109/fastboot-identity.json' | ConvertFrom-Json).serial
$build=Get-Content -Raw -LiteralPath "$out/rollback140-build-validation.json" | ConvertFrom-Json
$q=Get-Content -Raw -LiteralPath "$out/rollback-quiesce-validation.json" | ConvertFrom-Json
$bootId=(Get-Content -Raw -LiteralPath "$out/rejected-boot-id-private.txt").Trim()
if ($serial -notmatch '^[a-z0-9]{8}$' -or $bootId -notmatch '^[a-f0-9-]{36}$') {throw 'Private identity guard missing'}
if ($build.host_actual_function_cases -ne 12 -or !$build.kernel_build_no_warnings -or !$build.rollback140_bundle_verified -or !$build.all_770_modules_byte_identical132 -or !$build.dtb_byte_identical132 -or !$build.four_artifacts_fresh_hash_verified) {throw 'Candidate compatibility proof missing'}
if (!$q.quiesce_audit_pass -or $q.boot_id -ne $bootId -or !$q.all_remoteprocs_offline -or !$q.no_drm_userspace_clients) {throw 'Current boot quiesce proof missing'}
if ($q.taint -ne 0 -or !$q.known_shutdown_faults_transition_only -or $q.shutdown_tx_dma_failures -ne 70 -or !$q.dma_null_channel_state_down_verified -or $q.current_kernel -ne 143 -or $q.target_kernel -ne 140) {throw 'Exact rejected-kernel shutdown fault proof missing'}
if ((Get-Content -Raw -LiteralPath "$out/$prefix-freeze.out") -notmatch 'K143_F2FS_FROZEN_FOR_BOOTLOADER') {throw 'Freeze receipt missing'}
$events=Get-Content -LiteralPath "$out/$prefix-f1-wsl.events.jsonl" | ForEach-Object {$_ | ConvertFrom-Json}
if (@($events | Where-Object {$_.event -eq 'out_submit'}).Count -ne 1 -or @($events | Where-Object {$_.event -eq 'out_complete' -and $_.length -eq 2}).Count -ne 1) {throw 'Single completed transition OUT missing'}
if (@($events | Where-Object {$_.event -eq 'receipt' -and $_.text -eq 'F1'}).Count -ne 0 -or @($events | Where-Object {$_.event -eq 'read_error' -and $_.error -match 'Input/Output Error'}).Count -ne 1) {throw 'Recorded missing-ACK transition changed'}
$stateDevices=Get-Content -Raw -LiteralPath "$out/rollback140-state-devices-private.log"
$stateProduct=Get-Content -Raw -LiteralPath "$out/rollback140-state-product-private.log"
if ($stateDevices -notmatch ('(?im)^'+[regex]::Escape($serial)+'\s+fastboot\s*$') -or $stateProduct -notmatch 'product:\s*msmnile') {throw 'Independent actual bootloader state proof missing'}
$image="E:/edk2-samurai-out/kernel140/logdump-k140-dma-diagnostic.img"
$meta=@($build.artifacts | Where-Object {$_.role -eq 'logdump'})
if ($meta.Count -ne 1 -or (Get-Item -LiteralPath $image).Length -ne 67108864 -or (Get-FileHash -LiteralPath $image).Hash.ToLowerInvariant() -ne $meta[0].sha256) {throw 'Candidate bytes changed'}
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
$geometry=Invoke-Fastboot 'size-logdump' @('-s',$serial,'getvar','partition-size:logdump')
if ($geometry -notmatch 'partition-size:logdump:\s*(0x[0-9a-fA-F]+)' -or [Convert]::ToInt64($Matches[1].Substring(2),16) -ne 67108864) {throw 'Partition geometry mismatch'}
$text=Invoke-Fastboot 'flash-logdump' @('-s',$serial,'flash','logdump',$image)
if ($text -notmatch "Writing 'logdump'\s+OKAY" -or $text -match 'FAILED') {throw 'Flash completion unconfirmed'}
$null=Invoke-Fastboot 'reboot' @('-s',$serial,'reboot')
[ordered]@{stage=143;flash_success=$true;kernel_build=140;software_generation=132;unsubmitted_unwind_applied=$true;partitions=@('logdump');userdata_bulk_flash_or_erase=$false;rejected143_f1_receipt_missing=$true;single_out_complete_verified=$true;actual_expected_fastboot_identity_and_product_verified=$true;transition_not_replayed=$true;runtime_validation_pending=$true;goal_complete=$false} | ConvertTo-Json | Set-Content -Encoding utf8NoBOM -LiteralPath "$out/rollback-flash-validation.json"
Write-Output 'K143_RESTORED140_LOGDUMP_FLASH_CONFIRMED_RUNTIME_PENDING'
