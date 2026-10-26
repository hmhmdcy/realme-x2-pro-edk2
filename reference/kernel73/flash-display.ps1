$ErrorActionPreference='Stop'
$fb='C:\Users\cy122\Downloads\platform-tools\platform-tools\fastboot.exe'
$out='E:\edk2-samurai-out\kernel73'
function Invoke-DisplayFastboot([string]$Name,[string[]]$Arguments,[int]$TimeoutSeconds) {
    $proc=$null
    try {
        if (Test-Path -LiteralPath "$out\$Name.out") {throw 'Use a new output prefix'}
        $proc=Start-Process -FilePath $fb -ArgumentList $Arguments -WindowStyle Hidden -PassThru -RedirectStandardOutput "$out\$Name.out" -RedirectStandardError "$out\$Name.err"
        if (!$proc.WaitForExit($TimeoutSeconds*1000)) {throw "$Name timed out"}
        $proc.WaitForExit()
        if ($proc.ExitCode -ne 0) {throw "$Name exit $($proc.ExitCode)"}
        return ((Get-Content "$out\$Name.out" -Raw)+(Get-Content "$out\$Name.err" -Raw))
    } finally {
        if ($proc) {
            if (!$proc.HasExited) {$proc.Kill();$proc.WaitForExit()}
            $proc.Dispose()
        }
    }
}
$audit=Get-Content "$out\firmware-validation.json" -Raw | ConvertFrom-Json
if (!$audit.other_executable_bytes_unchanged -or !$audit.semantic_dtb_changes.only_native_display_changes) {throw 'Firmware audit failed'}
$cpio=Get-Content "$out\initramfs-validation.json" -Raw | ConvertFrom-Json
if (!$cpio.root_ownership_mapping_pass -or !$cpio.command_symlinks_pass -or !$cpio.private_client_key_absent) {throw 'Initramfs audit failed'}
$events=Get-Content "$out\display-f1-wsl.events.jsonl" | ForEach-Object {$_ | ConvertFrom-Json}
if (!@($events | Where-Object {$_.event -eq 'receipt' -and $_.text -eq 'F1'}).Count) {throw 'No fresh F1 receipt'}
foreach ($pair in @(
    @('boot-before.img','a4f4b75a52ec13a9b0b5cd4ebd678daa9a9dafd36548ce82ce4602a1fbcc15db'),
    @('logdump-before.img','13a8263dac6c75f909b6fa8dc89520949c7009ddcb9de2b2a5f6125e26d4292b'),
    @('boot-k73-display.img','57508887131ae55cf9465fa1a44280fa45b507a3439345ffe635dc7544eaa999'),
    @('logdump-k73-display.img','a4435ab347d3e857de88183b6d07969b47306cde1a5370489c95f384935968da'))) {
    if ((Get-FileHash "$out\$($pair[0])").Hash.ToLowerInvariant() -ne $pair[1]) {throw "Image hash mismatch: $($pair[0])"}
}
$usb=(& 'C:\Program Files\usbipd-win\usbipd.exe' list | Out-String)
if ($usb -match '(?m)^6-5\s+05c6:9505\s+[^\r\n]*Attached') {throw 'EUD still attached'}
$devices=Invoke-DisplayFastboot 'confirm-devices' @('devices') 15
if ($devices -notmatch '(?im)^62bc28a1\s+fastboot\s*$') {throw 'Phone not independently enumerated in fastboot'}
$product=Invoke-DisplayFastboot 'confirm-product' @('-s','62bc28a1','getvar','product') 15
if ($product -notmatch 'product:\s*msmnile') {throw 'Unexpected product'}
foreach ($part in @('boot','logdump')) {
    $size=Invoke-DisplayFastboot "confirm-size-$part" @('-s','62bc28a1','getvar',"partition-size:$part") 15
    if ($size -notmatch "partition-size:${part}:\s*(0x[0-9a-fA-F]+)") {throw "Partition size missing: $part"}
    $partitionBytes=[Convert]::ToInt64($Matches[1].Substring(2),16)
    $image="$out\$part-k73-display.img"
    if ((Get-Item $image).Length -gt $partitionBytes) {throw 'Image exceeds partition'}
    if ($part -eq 'logdump' -and $partitionBytes -ne 67108864) {throw 'Unexpected logdump size'}
}
foreach ($part in @('logdump','boot')) {
    $flash=Invoke-DisplayFastboot "flash-$part" @('-s','62bc28a1','flash',$part,"$out\$part-k73-display.img") 60
    if ($flash -notmatch "Writing '$part'\s+OKAY") {throw 'Successful write not observed'}
    $flash
}
$reboot=Invoke-DisplayFastboot 'reboot' @('-s','62bc28a1','reboot') 15
[ordered]@{utc=[DateTime]::UtcNow.ToString('o');serial='62bc28a1';product='msmnile';flashed_partitions=@('logdump','boot');flash_success=$true;reboot_success=$true;processes_disposed=$true;userdata_written=$false;gpt_written=$false} | ConvertTo-Json -Depth 4 | Set-Content "$out\flash-validation.json"
$reboot
