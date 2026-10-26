param([ValidatePattern('^[a-z0-9-]+$')][string]$Attempt='first')
$ErrorActionPreference='Stop'
$k109fb='C:\Users\cy122\Downloads\platform-tools\platform-tools\fastboot.exe'
$k109out='E:\edk2-samurai-out\kernel109'
$k109serial=(Get-Content "$k109out\fastboot-identity.json" -Raw | ConvertFrom-Json).serial
if ($k109serial -notmatch '^[a-z0-9]{8}$') {throw 'Verified phone serial missing'}
function Invoke-K109Fastboot([string]$Name,[string[]]$Arguments,[int]$Seconds) {
    $Name="$Attempt-$Name"; $proc=$null
    try {
        if (Test-Path -LiteralPath "$k109out\$Name.out") {throw 'Use a fresh output prefix'}
        $proc=Start-Process -FilePath $k109fb -ArgumentList $Arguments -WindowStyle Hidden -PassThru -RedirectStandardOutput "$k109out\$Name.out" -RedirectStandardError "$k109out\$Name.err"
        if (!$proc.WaitForExit($Seconds*1000)) {throw "$Name timed out; inspect device before retrying"}
        $proc.WaitForExit()
        if ($proc.ExitCode -ne 0) {throw "$Name exited $($proc.ExitCode)"}
        return ((Get-Content "$k109out\$Name.out" -Raw)+(Get-Content "$k109out\$Name.err" -Raw))
    } finally {
        if ($proc) {
            if (!$proc.HasExited) {$proc.Kill();$proc.WaitForExit()}
            $proc.Dispose()
        }
    }
}
$a=Get-Content "$k109out\candidate-validation.json" -Raw | ConvertFrom-Json
if (!$a.candidate_audit_pass -or !$a.userdata_authorized -or !$a.dtb_byte_identical -or !$a.firmware_boot_unchanged -or $a.nv_partition_writes -or $a.gpt_writes -or $a.kernel_build -ne 109) {throw 'Candidate audit failed'}
if (($a.flash_partitions -join ',') -ne 'userdata,logdump') {throw 'Unexpected scope'}
foreach ($item in @(@('boot-partition-before.img',$a.full_backup_boot_sha256),@('logdump-before.img',$a.full_backup_logdump_sha256),@('preflash.tar',$a.preflash_sha256),@('logdump-k109-pmos.img',$a.logdump_sha256),@('samurai-rootfs-f2fs.simg',$a.rootfs_sha256))) {
    if ((Get-FileHash -LiteralPath "$k109out\$($item[0])").Hash.ToLowerInvariant() -ne $item[1]) {throw 'Artifact/rollback checksum mismatch'}
}
$stop=Get-Content "$k109out\stop-connectivity-final.log" -Raw
if ($stop -notmatch 'CONNECTIVITY_STOPPED' -or $stop -notmatch [regex]::Escape($a.before_boot_id)) {throw 'Controlled stop evidence missing'}
$events=Get-Content "$k109out\connectivity-f1-wsl.events.jsonl" | ForEach-Object {$_ | ConvertFrom-Json}
if (!@($events | Where-Object {$_.event -eq 'receipt' -and $_.text -eq 'F1'}).Count) {throw 'Fresh F1 receipt missing'}
$usb=(& 'C:\Program Files\usbipd-win\usbipd.exe' list | Out-String)
if ($usb -match '(?m)^6-5\s+05c6:9505\s+[^\r\n]*Attached') {throw 'EUD still attached'}
$devices=Invoke-K109Fastboot 'devices' @('devices') 15
if ($devices -notmatch ('(?im)^'+[regex]::Escape($k109serial)+'\s+fastboot\s*$')) {throw 'Independent fastboot enumeration failed'}
$product=Invoke-K109Fastboot 'product' @('-s',$k109serial,'getvar','product') 15
if ($product -notmatch 'product:\s*msmnile') {throw 'Wrong product'}
foreach ($spec in @(@('userdata',[int64]119033245696),@('logdump',[int64]67108864))) {
    $r=Invoke-K109Fastboot "size-$($spec[0])" @('-s',$k109serial,'getvar',"partition-size:$($spec[0])") 15
    if ($r -notmatch ('partition-size:'+ $spec[0]+':\s*(0x[0-9a-fA-F]+)')) {throw 'Partition size missing'}
    if ([Convert]::ToInt64($Matches[1].Substring(2),16) -ne $spec[1]) {throw 'Partition size mismatch'}
}
if ((Get-Item "$k109out\logdump-k109-pmos.img").Length -ne 67108864 -or (Get-Item "$k109out\samurai-rootfs-f2fs.simg").Length -ne $a.rootfs_sparse_bytes) {throw 'Image size changed'}
# The user authorized replacing Android userdata. Erase before sparse writes
# ensures DONT_CARE extents cannot inherit old encrypted partition contents.
$r=Invoke-K109Fastboot 'erase-userdata' @('-s',$k109serial,'erase','userdata') 120
if ($r -notmatch "Erasing 'userdata'\s+OKAY") {throw 'Erase success not confirmed'}
Write-Output 'USERDATA_ERASE_CONFIRMED'
$r=Invoke-K109Fastboot 'flash-userdata' @('-s',$k109serial,'-S','256M','flash','userdata',"$k109out\samurai-rootfs-f2fs.simg") 240
if ($r -notmatch "Writing 'userdata'[^\r\n]*OKAY" -or $r -match 'FAILED') {throw 'Rootfs write success not confirmed'}
Write-Output 'USERDATA_F2FS_ROOTFS_FLASH_CONFIRMED'
$r=Invoke-K109Fastboot 'flash-logdump' @('-s',$k109serial,'flash','logdump',"$k109out\logdump-k109-pmos.img") 90
if ($r -notmatch "Writing 'logdump'\s+OKAY") {throw 'Kernel write success not confirmed'}
Write-Output 'KERNEL109_LOGDUMP_FLASH_CONFIRMED'
$null=Invoke-K109Fastboot 'reboot' @('-s',$k109serial,'reboot') 15
[ordered]@{utc=[DateTime]::UtcNow.ToString('o');partitions_flashed=@('userdata','logdump');userdata_erased=$true;userdata_bytes=$a.userdata_bytes;boot_unchanged=$true;rootfs_sha256=$a.rootfs_sha256;logdump_sha256=$a.logdump_sha256;flash_success=$true;reboot_success=$true;goal_complete=$false} | ConvertTo-Json | Set-Content -Encoding utf8NoBOM "$k109out\flash-validation.json"
Write-Output 'FLASH_AND_REBOOT_COMPLETE; HARDWARE_BOOT_VALIDATION_PENDING'
