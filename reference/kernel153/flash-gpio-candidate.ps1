param([ValidatePattern('^[a-z0-9-]+$')][string]$Prefix='gpio-first')
$ErrorActionPreference='Stop'
$out='E:/edk2-samurai-out/kernel153'
$fb='C:/Users/cy122/Downloads/platform-tools/platform-tools/fastboot.exe'
$serial=(Get-Content -Raw -LiteralPath 'E:/edk2-samurai-out/kernel109/fastboot-identity.json' | ConvertFrom-Json).serial
$build=Get-Content -Raw -LiteralPath "$out/build-package-validation.json" | ConvertFrom-Json
$q=Get-Content -Raw -LiteralPath "$out/quiesce-validation.json" | ConvertFrom-Json
$bootId=(Get-Content -Raw -LiteralPath "$out/source-boot-id-private.txt").Trim()
if (!$build.modules770_byte_identical132 -or !$build.config_unchanged -or !$build.dtb_unchanged -or !$build.fat_check_pass -or $build.build_warnings -ne 0) {throw 'Candidate verification missing'}
if (!$q.quiesce_audit_pass -or $q.boot_id -ne $bootId -or $q.current_kernel -ne 147 -or $q.target_kernel -ne 153 -or !$q.no_new_gpu_faults) {throw 'Fresh current145 state verification missing'}
if ((Get-Content -Raw -LiteralPath "$out/$Prefix-freeze.out") -notmatch 'K153_F2FS_FROZEN_FOR_BOOTLOADER') {throw 'Freeze receipt missing'}
$events=Get-Content -LiteralPath "$out/$Prefix-f1-wsl.events.jsonl" | ForEach-Object {$_ | ConvertFrom-Json}
if (@($events | Where-Object {$_.event -eq 'receipt' -and $_.text -eq 'F1'}).Count -ne 1 -or @($events | Where-Object {$_.event -eq 'out_submit'}).Count -ne 1) {throw 'Single F1 transition missing'}
$image="$out/logdump-k153-panel-handoff.img"
if ((Get-FileHash -LiteralPath $image).Hash.ToLowerInvariant() -ne $build.logdump_sha256) {throw 'Candidate hash mismatch'}
function Invoke-CurrentFastboot([string]$Name,[string[]]$Arguments) {
    $log="$out/$Prefix-$Name-private.log"
    if (Test-Path -LiteralPath $log) {throw 'Operation already has a log; inspect state'}
    & $fb @Arguments *> $log
    if ($LASTEXITCODE -ne 0) {throw "Fastboot $Name failed; inspect state"}
    return (Get-Content -Raw -LiteralPath $log)
}
$devices=Invoke-CurrentFastboot 'devices' @('devices')
if ($devices -notmatch ('(?im)^'+[regex]::Escape($serial)+'\s+fastboot\s*$')) {throw 'Device identity mismatch'}
$product=Invoke-CurrentFastboot 'product' @('-s',$serial,'getvar','product')
if ($product -notmatch 'product:\s*msmnile') {throw 'Product mismatch'}
$geometry=Invoke-CurrentFastboot 'size-logdump' @('-s',$serial,'getvar','partition-size:logdump')
if ($geometry -notmatch 'partition-size:logdump:\s*(0x[0-9a-fA-F]+)' -or [Convert]::ToInt64($Matches[1].Substring(2),16) -ne 67108864) {throw 'Partition geometry mismatch'}
$flash=Invoke-CurrentFastboot 'flash-logdump' @('-s',$serial,'flash','logdump',$image)
if ($flash -notmatch "Writing 'logdump'\s+OKAY" -or $flash -match 'FAILED') {throw 'Write completion unconfirmed'}
$null=Invoke-CurrentFastboot 'reboot' @('-s',$serial,'reboot')
[ordered]@{stage=153;flash_success=$true;partitions=@('logdump');kernel_build=153;runtime_validation_pending=$true} | ConvertTo-Json | Set-Content -LiteralPath "$out/flash-validation.json" -Encoding utf8NoBOM
Write-Output K153_CCU_CANDIDATE_LOGDUMP_FLASH_CONFIRMED
