$ErrorActionPreference='Stop'
$k84fb='C:\Users\cy122\Downloads\platform-tools\platform-tools\fastboot.exe'
$k84out='E:\edk2-samurai-out\kernel84'
function Invoke-K72Fastboot([string]$Name,[string[]]$Arguments,[int]$TimeoutSeconds) {
    $proc=$null
    try {
        if (Test-Path -LiteralPath "$k84out\$Name.out") { throw 'Use a new output prefix' }
        $proc=Start-Process -FilePath $k84fb -ArgumentList $Arguments -WindowStyle Hidden -PassThru -RedirectStandardOutput "$k84out\$Name.out" -RedirectStandardError "$k84out\$Name.err"
        if (!$proc.WaitForExit($TimeoutSeconds*1000)) { throw "$Name timed out" }
        $proc.WaitForExit()
        if ($proc.ExitCode -ne 0) { throw "$Name exit $($proc.ExitCode)" }
        return ((Get-Content "$k84out\$Name.out" -Raw)+(Get-Content "$k84out\$Name.err" -Raw))
    } finally {
        if ($proc) {
            if (!$proc.HasExited) { $proc.Kill(); $proc.WaitForExit() }
            $proc.Dispose()
        }
    }
}
$audit=Get-Content "$k84out\candidate-validation.json" -Raw | ConvertFrom-Json
if (!$audit.candidate_audit_pass -or !$audit.only_logdump_write_required -or !$audit.initramfs_cpio_byte_identical -or !$audit.hardware_driver_configuration_preserved) {throw 'Candidate audit failed'}
$guard=Get-Content "$k84out\guard-before-flash.txt" -Raw
if (!$guard.StartsWith("87753933-4992-45d2-aaf5-d9db9c11d1a3") -or $guard -notmatch '08edf9bcc1c55977169b0a8fd9f963805ba98d0423929e09e17bb9f811ca7405' -or $guard -notmatch '607fc6b4b0caba8ca5c7ea6677fd8259c81a216f91b2d6de7603e3f56d9881d0') {throw 'Live partition guard absent'}
if ((Get-FileHash "$k84out\boot-before.img").Hash.ToLowerInvariant() -ne '08edf9bcc1c55977169b0a8fd9f963805ba98d0423929e09e17bb9f811ca7405') {throw 'Boot preservation mismatch'}
$rollback='E:\edk2-samurai-out\kernel84\logdump-before.img'
if ((Get-FileHash $rollback).Hash.ToLowerInvariant() -ne '607fc6b4b0caba8ca5c7ea6677fd8259c81a216f91b2d6de7603e3f56d9881d0') {throw 'Rollback hash mismatch'}
$events=Get-Content "$k84out\trace-f1-wsl.events.jsonl" | ForEach-Object {$_ | ConvertFrom-Json}
if (!@($events | Where-Object {$_.event -eq 'receipt' -and $_.text -eq 'F1'}).Count) {throw 'No current F1 receipt'}
$usb=(& 'C:\Program Files\usbipd-win\usbipd.exe' list | Out-String)
if ($usb -match '(?m)^6-5\s+05c6:9505\s+[^\r\n]*Attached') {throw 'EUD still attached'}
$devices=''
for ($attempt=1; $attempt -le 10; $attempt++) {
    $devices=Invoke-K72Fastboot "trace-confirm-devices-$attempt" @('devices') 15
    if ($devices -match '(?im)^62bc28a1\s+fastboot\s*$') {break}
    Start-Sleep -Milliseconds 1000
}
if ($devices -notmatch '(?im)^62bc28a1\s+fastboot\s*$') {throw 'Phone not independently enumerated in fastboot'}
$product=Invoke-K72Fastboot 'trace-confirm-product' @('-s','62bc28a1','getvar','product') 15
if ($product -notmatch 'product:\s*msmnile') {throw 'Unexpected product'}
$size=Invoke-K72Fastboot 'trace-confirm-size-logdump' @('-s','62bc28a1','getvar','partition-size:logdump') 15
if ($size -notmatch 'partition-size:logdump:\s*(0x[0-9a-fA-F]+)') {throw 'Partition size missing'}
$partitionBytes=[Convert]::ToInt64($Matches[1].Substring(2),16)
$image="$k84out\logdump-k84-trace.img"
$hash=(Get-FileHash $image).Hash.ToLowerInvariant()
if ($partitionBytes -ne 67108864 -or (Get-Item $image).Length -ne 67108864 -or $hash -ne '8bb97ccb828dc8ccfaeb856be00b9a83f3b9fc57340208a24a7f9a51d88d8abe') {throw 'Image/partition/hash mismatch'}
$flash=Invoke-K72Fastboot 'trace-flash-logdump' @('-s','62bc28a1','flash','logdump',$image) 60
if ($flash -notmatch "Writing 'logdump'\s+OKAY") {throw 'Successful write not observed'}
$flash
$reboot=Invoke-K72Fastboot 'trace-reboot' @('-s','62bc28a1','reboot') 15
[ordered]@{utc=[DateTime]::UtcNow.ToString('o');serial='62bc28a1';product='msmnile';flashed_partitions=@('logdump');partition_bytes=$partitionBytes;image_sha256=$hash;flash_success=$true;reboot_success=$true;processes_disposed=$true;boot_written=$false;userdata_written=$false;gpt_written=$false} | ConvertTo-Json -Depth 4 | Set-Content "$k84out\trace-flash-validation.json"
$reboot
