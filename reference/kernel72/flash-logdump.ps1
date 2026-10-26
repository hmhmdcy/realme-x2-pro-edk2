$ErrorActionPreference='Stop'
$k72fb='C:\Users\cy122\Downloads\platform-tools\platform-tools\fastboot.exe'
$k72out='E:\edk2-samurai-out\kernel72'
function Invoke-K72Fastboot([string]$Name,[string[]]$Arguments,[int]$TimeoutSeconds) {
    $proc=$null
    try {
        if (Test-Path -LiteralPath "$k72out\$Name.out") { throw 'Use a new output prefix' }
        $proc=Start-Process -FilePath $k72fb -ArgumentList $Arguments -WindowStyle Hidden -PassThru -RedirectStandardOutput "$k72out\$Name.out" -RedirectStandardError "$k72out\$Name.err"
        if (!$proc.WaitForExit($TimeoutSeconds*1000)) { throw "$Name timed out" }
        $proc.WaitForExit()
        if ($proc.ExitCode -ne 0) { throw "$Name exit $($proc.ExitCode)" }
        return ((Get-Content "$k72out\$Name.out" -Raw)+(Get-Content "$k72out\$Name.err" -Raw))
    } finally {
        if ($proc) {
            if (!$proc.HasExited) { $proc.Kill(); $proc.WaitForExit() }
            $proc.Dispose()
        }
    }
}
$audit=Get-Content "$k72out\initramfs-validation.json" -Raw | ConvertFrom-Json
if (!$audit.root_ownership_mapping_pass -or !$audit.command_symlinks_pass -or !$audit.private_client_key_absent) {throw 'Initramfs audit failed'}
$rollback='E:\edk2-samurai-out\kernel71\logdump-k71-touch.img'
if ((Get-FileHash $rollback).Hash.ToLowerInvariant() -ne 'f6837573c908eddad7a2d8d0ab494c259ff99a9a5b85878e3b6747d40b2d3fb8') {throw 'Rollback hash mismatch'}
$usb=(& 'C:\Program Files\usbipd-win\usbipd.exe' list | Out-String)
if ($usb -match '(?m)^6-5\s+05c6:9505\s+[^\r\n]*Attached') {throw 'EUD still attached'}
$devices=Invoke-K72Fastboot 'confirm-devices' @('devices') 15
if ($devices -notmatch '(?im)^62bc28a1\s+fastboot\s*$') {throw 'Phone not independently enumerated in fastboot'}
$product=Invoke-K72Fastboot 'confirm-product' @('-s','62bc28a1','getvar','product') 15
if ($product -notmatch 'product:\s*msmnile') {throw 'Unexpected product'}
$size=Invoke-K72Fastboot 'confirm-size-logdump' @('-s','62bc28a1','getvar','partition-size:logdump') 15
if ($size -notmatch 'partition-size:logdump:\s*(0x[0-9a-fA-F]+)') {throw 'Partition size missing'}
$partitionBytes=[Convert]::ToInt64($Matches[1].Substring(2),16)
$image="$k72out\logdump-k72-ncm-ssh.img"
$hash=(Get-FileHash $image).Hash.ToLowerInvariant()
if ($partitionBytes -ne 67108864 -or (Get-Item $image).Length -ne 67108864 -or $hash -ne '13a8263dac6c75f909b6fa8dc89520949c7009ddcb9de2b2a5f6125e26d4292b') {throw 'Image/partition/hash mismatch'}
$flash=Invoke-K72Fastboot 'flash-logdump' @('-s','62bc28a1','flash','logdump',$image) 60
if ($flash -notmatch "Writing 'logdump'\s+OKAY") {throw 'Successful write not observed'}
$flash
$reboot=Invoke-K72Fastboot 'reboot' @('-s','62bc28a1','reboot') 15
[ordered]@{utc=[DateTime]::UtcNow.ToString('o');serial='62bc28a1';product='msmnile';flashed_partitions=@('logdump');partition_bytes=$partitionBytes;image_sha256=$hash;flash_success=$true;reboot_success=$true;processes_disposed=$true;boot_written=$false;userdata_written=$false;gpt_written=$false} | ConvertTo-Json -Depth 4 | Set-Content "$k72out\flash-validation.json"
$reboot
