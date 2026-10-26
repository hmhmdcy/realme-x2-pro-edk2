$ErrorActionPreference='Stop'
$k73fb='C:\Users\cy122\Downloads\platform-tools\platform-tools\fastboot.exe'
$k73out='E:\edk2-samurai-out\kernel73'
function Invoke-K72Fastboot([string]$Name,[string[]]$Arguments,[int]$TimeoutSeconds) {
    $proc=$null
    try {
        if (Test-Path -LiteralPath "$k73out\$Name.out") { throw 'Use a new output prefix' }
        $proc=Start-Process -FilePath $k73fb -ArgumentList $Arguments -WindowStyle Hidden -PassThru -RedirectStandardOutput "$k73out\$Name.out" -RedirectStandardError "$k73out\$Name.err"
        if (!$proc.WaitForExit($TimeoutSeconds*1000)) { throw "$Name timed out" }
        $proc.WaitForExit()
        if ($proc.ExitCode -ne 0) { throw "$Name exit $($proc.ExitCode)" }
        return ((Get-Content "$k73out\$Name.out" -Raw)+(Get-Content "$k73out\$Name.err" -Raw))
    } finally {
        if ($proc) {
            if (!$proc.HasExited) { $proc.Kill(); $proc.WaitForExit() }
            $proc.Dispose()
        }
    }
}
$audit=Get-Content "$k73out\initramfs-validation.json" -Raw | ConvertFrom-Json
if (!$audit.root_ownership_mapping_pass -or !$audit.command_symlinks_pass -or !$audit.private_client_key_absent) {throw 'Initramfs audit failed'}
$rollback='E:\edk2-samurai-out\kernel73\logdump-k73-display.img'
if ((Get-FileHash $rollback).Hash.ToLowerInvariant() -ne 'a4435ab347d3e857de88183b6d07969b47306cde1a5370489c95f384935968da') {throw 'Rollback hash mismatch'}
$usb=(& 'C:\Program Files\usbipd-win\usbipd.exe' list | Out-String)
if ($usb -match '(?m)^6-5\s+05c6:9505\s+[^\r\n]*Attached') {throw 'EUD still attached'}
$devices=Invoke-K72Fastboot 'deps-confirm-devices' @('devices') 15
if ($devices -notmatch '(?im)^62bc28a1\s+fastboot\s*$') {throw 'Phone not independently enumerated in fastboot'}
$product=Invoke-K72Fastboot 'deps-confirm-product' @('-s','62bc28a1','getvar','product') 15
if ($product -notmatch 'product:\s*msmnile') {throw 'Unexpected product'}
$size=Invoke-K72Fastboot 'deps-confirm-size-logdump' @('-s','62bc28a1','getvar','partition-size:logdump') 15
if ($size -notmatch 'partition-size:logdump:\s*(0x[0-9a-fA-F]+)') {throw 'Partition size missing'}
$partitionBytes=[Convert]::ToInt64($Matches[1].Substring(2),16)
$image="$k73out\logdump-k73-display-deps.img"
$hash=(Get-FileHash $image).Hash.ToLowerInvariant()
if ($partitionBytes -ne 67108864 -or (Get-Item $image).Length -ne 67108864 -or $hash -ne 'c7778d45c336b35cf75c2842c083b513343f59a0a1864fe52ad2105d3d55e6c7') {throw 'Image/partition/hash mismatch'}
$flash=Invoke-K72Fastboot 'deps-flash-logdump' @('-s','62bc28a1','flash','logdump',$image) 60
if ($flash -notmatch "Writing 'logdump'\s+OKAY") {throw 'Successful write not observed'}
$flash
$reboot=Invoke-K72Fastboot 'deps-reboot' @('-s','62bc28a1','reboot') 15
[ordered]@{utc=[DateTime]::UtcNow.ToString('o');serial='62bc28a1';product='msmnile';flashed_partitions=@('logdump');partition_bytes=$partitionBytes;image_sha256=$hash;flash_success=$true;reboot_success=$true;processes_disposed=$true;boot_written=$false;userdata_written=$false;gpt_written=$false} | ConvertTo-Json -Depth 4 | Set-Content "$k73out\deps-flash-validation.json"
$reboot
