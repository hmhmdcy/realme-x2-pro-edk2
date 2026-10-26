$ErrorActionPreference='Stop'
$k86fb='C:\Users\cy122\Downloads\platform-tools\platform-tools\fastboot.exe'
$k86out='E:\edk2-samurai-out\kernel86'
# Session86 captured new display faults before this candidate could be tested.
# Do not use the stale guard or reflash without a new fault-reviewed session.
throw 'Candidate #87 is untested; session86 display fault evidence must be reviewed before a new deployment'
function Invoke-K72Fastboot([string]$Name,[string[]]$Arguments,[int]$TimeoutSeconds) {
    $proc=$null
    try {
        if (Test-Path -LiteralPath "$k86out\$Name.out") { throw 'Use a new output prefix' }
        $proc=Start-Process -FilePath $k86fb -ArgumentList $Arguments -WindowStyle Hidden -PassThru -RedirectStandardOutput "$k86out\$Name.out" -RedirectStandardError "$k86out\$Name.err"
        if (!$proc.WaitForExit($TimeoutSeconds*1000)) { throw "$Name timed out" }
        $proc.WaitForExit()
        if ($proc.ExitCode -ne 0) { throw "$Name exit $($proc.ExitCode)" }
        return ((Get-Content "$k86out\$Name.out" -Raw)+(Get-Content "$k86out\$Name.err" -Raw))
    } finally {
        if ($proc) {
            if (!$proc.HasExited) { $proc.Kill(); $proc.WaitForExit() }
            $proc.Dispose()
        }
    }
}
$audit=Get-Content "$k86out\candidate-final-validation.json" -Raw | ConvertFrom-Json
if (!$audit.candidate_audit_pass -or !$audit.only_logdump_write_required -or !$audit.initramfs_cpio_byte_identical -or !$audit.hardware_driver_configuration_preserved) {throw 'Candidate audit failed'}
$guard=Get-Content "$k86out\guard-before-final.txt" -Raw
if (!$guard.StartsWith("32bf2d8f-8dde-47dc-9b88-e87db9e95198") -or $guard -notmatch '08edf9bcc1c55977169b0a8fd9f963805ba98d0423929e09e17bb9f811ca7405' -or $guard -notmatch 'cf11644e32a138ff1319fe9e44529f1ef7b2a1907c1f8876c597f970a526d286') {throw 'Live partition guard absent'}
if ((Get-FileHash "E:\edk2-samurai-out\kernel84\boot-before.img").Hash.ToLowerInvariant() -ne '08edf9bcc1c55977169b0a8fd9f963805ba98d0423929e09e17bb9f811ca7405') {throw 'Boot preservation mismatch'}
$rollback='E:\edk2-samurai-out\kernel86\logdump-k86-input.img'
if ((Get-FileHash $rollback).Hash.ToLowerInvariant() -ne 'cf11644e32a138ff1319fe9e44529f1ef7b2a1907c1f8876c597f970a526d286') {throw 'Rollback hash mismatch'}
$events=Get-Content "$k86out\final-f1-wsl.events.jsonl" | ForEach-Object {$_ | ConvertFrom-Json}
if (!@($events | Where-Object {$_.event -eq 'receipt' -and $_.text -eq 'F1'}).Count) {throw 'No current F1 receipt'}
$usb=(& 'C:\Program Files\usbipd-win\usbipd.exe' list | Out-String)
if ($usb -match '(?m)^6-5\s+05c6:9505\s+[^\r\n]*Attached') {throw 'EUD still attached'}
$devices=''
for ($attempt=1; $attempt -le 10; $attempt++) {
    $devices=Invoke-K72Fastboot "final-confirm-devices-$attempt" @('devices') 15
    if ($devices -match '(?im)^62bc28a1\s+fastboot\s*$') {break}
    Start-Sleep -Milliseconds 1000
}
if ($devices -notmatch '(?im)^62bc28a1\s+fastboot\s*$') {throw 'Phone not independently enumerated in fastboot'}
$product=Invoke-K72Fastboot 'final-confirm-product' @('-s','62bc28a1','getvar','product') 15
if ($product -notmatch 'product:\s*msmnile') {throw 'Unexpected product'}
$size=Invoke-K72Fastboot 'final-confirm-size-logdump' @('-s','62bc28a1','getvar','partition-size:logdump') 15
if ($size -notmatch 'partition-size:logdump:\s*(0x[0-9a-fA-F]+)') {throw 'Partition size missing'}
$partitionBytes=[Convert]::ToInt64($Matches[1].Substring(2),16)
$image="$k86out\logdump-k86-final.img"
$hash=(Get-FileHash $image).Hash.ToLowerInvariant()
if ($partitionBytes -ne 67108864 -or (Get-Item $image).Length -ne 67108864 -or $hash -ne 'da6a23adbc663bc6526ac6f77a6e789b0a096c91ddbdedcc96265084aee7b7f7') {throw 'Image/partition/hash mismatch'}
$flash=Invoke-K72Fastboot 'final-flash-logdump' @('-s','62bc28a1','flash','logdump',$image) 60
if ($flash -notmatch "Writing 'logdump'\s+OKAY") {throw 'Successful write not observed'}
$flash
$reboot=Invoke-K72Fastboot 'final-reboot' @('-s','62bc28a1','reboot') 15
[ordered]@{utc=[DateTime]::UtcNow.ToString('o');serial='62bc28a1';product='msmnile';flashed_partitions=@('logdump');partition_bytes=$partitionBytes;image_sha256=$hash;flash_success=$true;reboot_success=$true;processes_disposed=$true;boot_written=$false;userdata_written=$false;gpt_written=$false} | ConvertTo-Json -Depth 4 | Set-Content "$k86out\final-flash-validation.json"
$reboot
# Restore the established COM/NCM attach path after reboot. This writes only
# COM_EN, VBUS_ATTACH and VBUS_INT; it does not write CHGR_EN or CHGR_INT.
$eudtool='E:\eud-host\eudtool.exe'
if ((Get-FileHash $eudtool).Hash.ToLowerInvariant() -ne '6fc91093235762ab82b08c33de2563dc214f98e52ea9025a80a58f278137a6bb') {throw 'EUD helper hash mismatch'}
$probe=''
for ($attempt=1; $attempt -le 15; $attempt++) {
    $probe=(& $eudtool probe | Out-String)
    $probe | Set-Content "$k86out\final-eud-probe-$attempt.txt"
    if ($LASTEXITCODE -eq 0 -and $probe -match 'resp \(4\): A1 28 BC 62') {break}
    Start-Sleep -Milliseconds 500
}
if ($probe -notmatch 'resp \(4\): A1 28 BC 62') {throw 'Expected EUD control identity absent'}
$attach=(& $eudtool com-up | Out-String)
$code=$LASTEXITCODE
$attach | Set-Content "$k86out\com-up-input.txt"
if ($code -ne 0 -or $attach -notmatch 'com-up done' -or $attach -notmatch 'CTL 0x07 payload=0x00000020' -or $attach -notmatch 'CTL 0x07 payload=0x00001000' -or $attach -notmatch 'CTL 0x07 payload=0x00002000' -or $attach -match 'payload=0x0000[4-8]000') {throw 'Established EUD attach did not complete'}
$attach
