param([ValidatePattern('^[a-z0-9-]+$')][string]$Prefix='ctl-final-read-first')
$ErrorActionPreference='Stop'
$out='E:\edk2-samurai-out\kernel119'
$candidateOut='E:\edk2-samurai-out\kernel118'
$fb='C:\Users\cy122\Downloads\platform-tools\platform-tools\fastboot.exe'
$serial=(Get-Content -LiteralPath 'E:\edk2-samurai-out\kernel109\fastboot-identity.json' -Raw | ConvertFrom-Json).serial
if ($serial -notmatch '^[a-z0-9]{8}$') {throw 'Verified device identity missing'}
$audit=Get-Content -LiteralPath "$candidateOut\candidate-package-validation.json" -Raw | ConvertFrom-Json
$build=Get-Content -LiteralPath "$candidateOut\kernel-build-validation.json" -Raw | ConvertFrom-Json
$guard=Get-Content -LiteralPath "$out\preflash-validation.json" -Raw | ConvertFrom-Json
if ($audit.candidate -ne 118 -or !$audit.fat_readback_exact -or !$audit.fat_check_pass -or !$audit.dtb_115_identical -or !$audit.boot_115_reused -or !$audit.module_115_export_abi_compatible -or ($audit.flash_partitions -join ',') -ne 'logdump') {throw 'Candidate scope rejected'}
if (!$build.full_image_modules_dtb_build_pass -or !$build.all_stripped_module_bytes_identical_excluding_build_id -or !$build.embedded_cpio_semantically_identical) {throw 'Kernel build validation missing'}
if (!$guard.preflash_audit_pass -or !$guard.live_backups_match -or !$guard.gpt18_unchanged -or !$guard.nv6_source4_vendor_preserved -or !$guard.persist_unchanged -or $guard.current_kernel -ne 115 -or $guard.target_kernel -ne 118) {throw 'Fresh device checkpoint absent'}
if ($guard.boot_id -ne (Get-Content -LiteralPath "$out\source-boot-id-private.txt" -Raw).Trim()) {throw 'Boot guard changed'}
foreach ($item in @(@("$out\boot-partition-before.img",$guard.before_boot_sha256),@("$out\logdump-before.img",$guard.before_logdump_sha256),@("$candidateOut\logdump-k118-ctl-final-read.img",$audit.logdump_sha256))) {
    if ((Get-FileHash -LiteralPath $item[0]).Hash.ToLowerInvariant() -ne $item[1]) {throw 'Candidate or rollback bytes changed'}
}
if ((Get-Content -LiteralPath "$out\$Prefix-freeze.out" -Raw) -notmatch 'KERNEL119_F2FS_FROZEN_FOR_BOOTLOADER') {throw 'No root freeze receipt'}
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
if ($usb -match '(?m)^6-5\s+05c6:9505\s+[^\r\n]*Attached') {throw 'EUD still owned by WSL'}
$devices=Invoke-CheckedFastboot 'devices' @('devices')
if ($devices -notmatch ('(?im)^'+[regex]::Escape($serial)+'\s+fastboot\s*$')) {throw 'Independent enumeration failed'}
$product=Invoke-CheckedFastboot 'product' @('-s',$serial,'getvar','product')
if ($product -notmatch 'product:\s*msmnile') {throw 'Unexpected product'}
foreach ($item in @(@('boot',[int64]100663296),@('logdump',[int64]67108864))) {
    $name=$item[0];$r=Invoke-CheckedFastboot "size-$name" @('-s',$serial,'getvar',"partition-size:$name")
    if ($r -notmatch ("partition-size:$name"+':\s*(0x[0-9a-fA-F]+)') -or [Convert]::ToInt64($Matches[1].Substring(2),16) -ne $item[1]) {throw 'Partition geometry changed'}
}
$file="$candidateOut\logdump-k118-ctl-final-read.img"
if ((Get-Item -LiteralPath $file).Length -ne 67108864) {throw 'Image length changed'}
$r=Invoke-CheckedFastboot 'flash-logdump' @('-s',$serial,'flash','logdump',$file) 90
if ($r -notmatch "Writing 'logdump'\s+OKAY" -or $r -match 'FAILED') {throw 'Flash completion not confirmed'}
Write-Output 'KERNEL118_LOGDUMP_FLASH_CONFIRMED'
$null=Invoke-CheckedFastboot 'reboot' @('-s',$serial,'reboot')
[ordered]@{flash_success=$true;kernel_build=118;partitions=@('logdump');boot_changed=$false;userdata_erased=$false;boot_sha256=$audit.boot_115_sha256;logdump_sha256=$audit.logdump_sha256;root_frozen_before_reboot=$true;hardware_test_pending=$true;goal_complete=$false} | ConvertTo-Json | Set-Content -LiteralPath "$out\$Prefix-flash-validation.json" -Encoding utf8NoBOM
Write-Output 'KERNEL118_LOGDUMP_FLASH_AND_REBOOT_COMPLETE; NATIVE_RUNTIME_CHECK_PENDING'
