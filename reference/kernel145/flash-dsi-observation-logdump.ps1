$ErrorActionPreference='Stop'
$out='E:/edk2-samurai-out/kernel145'
$prefix='dsi-raw-first'
$fb='C:/Users/cy122/Downloads/platform-tools/platform-tools/fastboot.exe'
$serial=(Get-Content -Raw -LiteralPath 'E:/edk2-samurai-out/kernel109/fastboot-identity.json' | ConvertFrom-Json).serial
$build=Get-Content -Raw -LiteralPath "$out/dsi-observation-build-package-validation.json" | ConvertFrom-Json
$q=Get-Content -Raw -LiteralPath "$out/quiesce-validation.json" | ConvertFrom-Json
$bootId=(Get-Content -Raw -LiteralPath "$out/source-boot-id-private.txt").Trim()
if ($serial -notmatch '^[a-z0-9]{8}$' -or $bootId -notmatch '^[a-f0-9-]{36}$') {throw 'Private identity guard missing'}
if ($build.host_actual_function_cases -ne 24 -or $build.eud_handoff_actual_function_cases -ne 26 -or !$build.kernel_build_no_warnings -or !$build.dsi_raw_state_trace_only -or !$build.eud_handoff144_preserved -or !$build.all_770_modules_byte_identical132 -or !$build.dtb_byte_identical132 -or !$build.four_artifacts_fresh_hash_verified) {throw 'Candidate compatibility proof missing'}
if (!$q.quiesce_audit_pass -or $q.boot_id -ne $bootId -or !$q.all_remoteprocs_offline -or !$q.no_drm_userspace_clients) {throw 'Current boot quiesce proof missing'}
if (!$q.shutdown_state_validated -or $q.taint -notin 0,512 -or ($q.taint -eq 512 -and !$q.known_warning_transition_only) -or $q.current_kernel -ne 140 -or $q.target_kernel -ne 145) {throw 'Fresh old-kernel shutdown proof missing'}
if ((Get-Content -Raw -LiteralPath "$out/$prefix-freeze.out") -notmatch 'K145_F2FS_FROZEN_FOR_BOOTLOADER') {throw 'Freeze receipt missing'}
$events=Get-Content -LiteralPath "$out/$prefix-f1-wsl.events.jsonl" | ForEach-Object {$_ | ConvertFrom-Json}
if (@($events | Where-Object {$_.event -eq 'receipt' -and $_.text -eq 'F1'}).Count -ne 1 -or @($events | Where-Object {$_.event -eq 'out_submit'}).Count -ne 1) {throw 'Single F1 transition missing'}
$recorder=Get-Content -Raw -LiteralPath "$out/early-recorder-install-validation.json" | ConvertFrom-Json
if (!$recorder.installed_recorder_three_files_exact -or !$recorder.one_new_boot_only) {throw 'Early startup recorder install receipt missing'}
$image="$out/logdump-k145-dsi-observation.img"
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
[ordered]@{stage=145;flash_success=$true;kernel_build=145;software_generation=132;unsubmitted_unwind_applied=$true;partitions=@('logdump');userdata_bulk_flash_or_erase=$false;runtime_validation_pending=$true;goal_complete=$false} | ConvertTo-Json | Set-Content -Encoding utf8NoBOM -LiteralPath "$out/flash-validation.json"
Write-Output 'K145_THREADED_CONSOLE_LOGDUMP_FLASH_CONFIRMED_RUNTIME_PENDING'
