param([ValidatePattern('^[a-z0-9-]+$')][string]$Prefix='sensor-power-first')
$ErrorActionPreference='Stop'
$out='E:\edk2-samurai-out\kernel115'
$fb='C:\Users\cy122\Downloads\platform-tools\platform-tools\fastboot.exe'
$serial=(Get-Content -LiteralPath 'E:\edk2-samurai-out\kernel109\fastboot-identity.json' -Raw | ConvertFrom-Json).serial
if ($serial -notmatch '^[a-z0-9]{8}$') {throw 'Verified device identity missing'}
$audit=Get-Content -LiteralPath "$out\candidate-validation.json" -Raw | ConvertFrom-Json
if (!$audit.ipa_enabled -or !$audit.own_ipa_firmware -or $audit.gsi_wait_bounded_ms -ne 1000 -or $audit.sensor_power_auto_enable -or !$audit.candidate_audit_pass -or $audit.kernel_build -ne 115 -or $audit.slpi_auto_boot -or !$audit.firmware_only_dtb_change -or !$audit.baseline_source_and_artifacts_preserved -or $audit.userdata_reformatted -or $audit.nv_partition_writes -or $audit.persist_partition_writes -or $audit.gpt_writes -or ($audit.flash_partitions -join ',') -ne 'boot,logdump') {throw 'Candidate scope/audit rejected'}
foreach ($item in @(@('boot-partition-before.img',$audit.before_boot_sha256),@('logdump-before.img',$audit.before_logdump_sha256),@('boot-partition-k115.img',$audit.boot_sha256),@('logdump-k115-ipa-zram.img',$audit.logdump_sha256))) {
    if ((Get-FileHash -LiteralPath "$out\$($item[0])").Hash.ToLowerInvariant() -ne $item[1]) {throw 'Candidate or rollback bytes changed'}
}
$guard=Get-Content -LiteralPath "$out\preflash-validation.json" -Raw | ConvertFrom-Json
if (!$guard.preflash_audit_pass -or !$guard.live_backups_match -or !$guard.nv_sources_unchanged -or !$guard.persist_unchanged) {throw 'Fresh device checkpoint absent'}
if ((Get-Content -LiteralPath "$out\$Prefix-freeze.out" -Raw) -notmatch 'KERNEL115_F2FS_FROZEN_FOR_BOOTLOADER') {throw 'No root freeze receipt'}
$events=Get-Content -LiteralPath "$out\$Prefix-f1-wsl.events.jsonl" | ForEach-Object {$_ | ConvertFrom-Json}
if (!@($events | Where-Object {$_.event -eq 'receipt' -and $_.text -eq 'F1'}).Count) {throw 'No fresh F1 receipt'}
function Invoke-CheckedFastboot([string]$Name,[string[]]$Arguments,[int]$Seconds=15) {
    $base="$out\$Prefix-$Name";$p=$null
    if (Test-Path -LiteralPath "$base.out") {throw 'Use a fresh flash prefix'}
    try {
        $p=Start-Process -FilePath $fb -ArgumentList $Arguments -WindowStyle Hidden -PassThru -RedirectStandardOutput "$base.out" -RedirectStandardError "$base.err"
        if (!$p.WaitForExit($Seconds*1000)) {throw 'Fastboot timed out; inspect before retrying'}
        $p.WaitForExit();if ($p.ExitCode -ne 0) {throw "Fastboot $Name failed"}
        return ((Get-Content -LiteralPath "$base.out" -Raw)+(Get-Content -LiteralPath "$base.err" -Raw))
    } finally {if ($p) {if (!$p.HasExited) {$p.Kill();$p.WaitForExit()};$p.Dispose()}}
}
$usb=(& 'C:\Program Files\usbipd-win\usbipd.exe' list | Out-String)
if ($usb -match '(?m)^6-5\s+05c6:9505\s+[^\r\n]*Attached') {throw 'EUD is still owned by WSL'}
$devices=Invoke-CheckedFastboot 'devices' @('devices')
if ($devices -notmatch ('(?im)^'+[regex]::Escape($serial)+'\s+fastboot\s*$')) {throw 'Independent enumeration failed'}
$product=Invoke-CheckedFastboot 'product' @('-s',$serial,'getvar','product')
if ($product -notmatch 'product:\s*msmnile') {throw 'Unexpected product'}
foreach ($item in @(@('boot',[int64]100663296),@('logdump',[int64]67108864))) {
    $name=$item[0];$r=Invoke-CheckedFastboot "size-$name" @('-s',$serial,'getvar',"partition-size:$name")
    if ($r -notmatch ("partition-size:$name"+':\s*(0x[0-9a-fA-F]+)') -or [Convert]::ToInt64($Matches[1].Substring(2),16) -ne $item[1]) {throw 'Partition geometry changed'}
}
foreach ($item in @(@('logdump','logdump-k115-ipa-zram.img',67108864),@('boot','boot-partition-k115.img',100663296))) {
    $name=$item[0];$file="$out\$($item[1])"
    if ((Get-Item -LiteralPath $file).Length -ne $item[2]) {throw 'Partition image length changed'}
    $r=Invoke-CheckedFastboot "flash-$name" @('-s',$serial,'flash',$name,$file) 90
    if ($r -notmatch ("Writing '$name'"+'\s+OKAY') -or $r -match 'FAILED') {throw 'Flash completion not confirmed'}
    Write-Output "KERNEL115_$($name.ToUpperInvariant())_FLASH_CONFIRMED"
}
$null=Invoke-CheckedFastboot 'reboot' @('-s',$serial,'reboot')
[ordered]@{flash_success=$true;kernel_build=115;partitions=@('logdump','boot');userdata_erased=$false;boot_sha256=$audit.boot_sha256;logdump_sha256=$audit.logdump_sha256;root_frozen_before_reboot=$true;slpi_auto_boot=$false;hardware_test_pending=$true} | ConvertTo-Json | Set-Content -LiteralPath "$out\$Prefix-flash-validation.json" -Encoding utf8NoBOM
Write-Output 'KERNEL115_FLASH_AND_REBOOT_COMPLETE; BOOT_AND_HARDWARE_CHECK_PENDING'
