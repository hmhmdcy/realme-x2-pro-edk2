$ErrorActionPreference='Stop'
$k75fb='C:\Users\cy122\Downloads\platform-tools\platform-tools\fastboot.exe'
$k75out='E:\edk2-samurai-out\kernel75'
function Invoke-K72Fastboot([string]$Name,[string[]]$Arguments,[int]$TimeoutSeconds) {
    $proc=$null
    try {
        if (Test-Path -LiteralPath "$k75out\$Name.out") { throw 'Use a new output prefix' }
        $proc=Start-Process -FilePath $k75fb -ArgumentList $Arguments -WindowStyle Hidden -PassThru -RedirectStandardOutput "$k75out\$Name.out" -RedirectStandardError "$k75out\$Name.err"
        if (!$proc.WaitForExit($TimeoutSeconds*1000)) { throw "$Name timed out" }
        $proc.WaitForExit()
        if ($proc.ExitCode -ne 0) { throw "$Name exit $($proc.ExitCode)" }
        return ((Get-Content "$k75out\$Name.out" -Raw)+(Get-Content "$k75out\$Name.err" -Raw))
    } finally {
        if ($proc) {
            if (!$proc.HasExited) { $proc.Kill(); $proc.WaitForExit() }
            $proc.Dispose()
        }
    }
}
$audit=Get-Content "$k75out\initramfs-validation.json" -Raw | ConvertFrom-Json
if (!$audit.root_ownership_mapping_pass -or !$audit.command_symlinks_pass -or !$audit.private_client_key_absent) {throw 'Initramfs audit failed'}
$rollback='E:\edk2-samurai-out\kernel75\logdump-before.img'
if ((Get-FileHash $rollback).Hash.ToLowerInvariant() -ne '8e43d13658a1d332c441f68a6008e7ebb855177b59fbeb447a196195239f1ee5') {throw 'Rollback hash mismatch'}
$events=Get-Content "$k75out\diagnostic-f1-wsl.events.jsonl" | ForEach-Object {$_ | ConvertFrom-Json}
if (!@($events | Where-Object {$_.event -eq 'receipt' -and $_.text -eq 'F1'}).Count) {throw 'No current F1 receipt'}
$usb=(& 'C:\Program Files\usbipd-win\usbipd.exe' list | Out-String)
if ($usb -match '(?m)^6-5\s+05c6:9505\s+[^\r\n]*Attached') {throw 'EUD still attached'}
$devices=''
for ($attempt=1; $attempt -le 10; $attempt++) {
    $devices=Invoke-K72Fastboot "diagnostic-ready-confirm-devices-$attempt" @('devices') 15
    if ($devices -match '(?im)^62bc28a1\s+fastboot\s*$') {break}
    Start-Sleep -Milliseconds 1000
}
if ($devices -notmatch '(?im)^62bc28a1\s+fastboot\s*$') {throw 'Phone not independently enumerated in fastboot'}
$product=Invoke-K72Fastboot 'diagnostic-ready-confirm-product' @('-s','62bc28a1','getvar','product') 15
if ($product -notmatch 'product:\s*msmnile') {throw 'Unexpected product'}
$size=Invoke-K72Fastboot 'diagnostic-ready-confirm-size-logdump' @('-s','62bc28a1','getvar','partition-size:logdump') 15
if ($size -notmatch 'partition-size:logdump:\s*(0x[0-9a-fA-F]+)') {throw 'Partition size missing'}
$partitionBytes=[Convert]::ToInt64($Matches[1].Substring(2),16)
$image="$k75out\logdump-k75-diagnostic.img"
$hash=(Get-FileHash $image).Hash.ToLowerInvariant()
if ($partitionBytes -ne 67108864 -or (Get-Item $image).Length -ne 67108864 -or $hash -ne '73dcc187c35dcacb0644f7672323688b7341b03972019547f1f0413c1772f050') {throw 'Image/partition/hash mismatch'}
$flash=Invoke-K72Fastboot 'diagnostic-flash-logdump' @('-s','62bc28a1','flash','logdump',$image) 60
if ($flash -notmatch "Writing 'logdump'\s+OKAY") {throw 'Successful write not observed'}
$flash
$reboot=Invoke-K72Fastboot 'diagnostic-reboot' @('-s','62bc28a1','reboot') 15
[ordered]@{utc=[DateTime]::UtcNow.ToString('o');serial='62bc28a1';product='msmnile';flashed_partitions=@('logdump');partition_bytes=$partitionBytes;image_sha256=$hash;flash_success=$true;reboot_success=$true;processes_disposed=$true;boot_written=$false;userdata_written=$false;gpt_written=$false} | ConvertTo-Json -Depth 4 | Set-Content "$k75out\diagnostic-flash-validation.json"
$reboot
