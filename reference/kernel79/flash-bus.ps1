$ErrorActionPreference='Stop'
$k79fb='C:\Users\cy122\Downloads\platform-tools\platform-tools\fastboot.exe'
$k79out='E:\edk2-samurai-out\kernel79'
function Invoke-K72Fastboot([string]$Name,[string[]]$Arguments,[int]$TimeoutSeconds) {
    $proc=$null
    try {
        if (Test-Path -LiteralPath "$k79out\$Name.out") { throw 'Use a new output prefix' }
        $proc=Start-Process -FilePath $k79fb -ArgumentList $Arguments -WindowStyle Hidden -PassThru -RedirectStandardOutput "$k79out\$Name.out" -RedirectStandardError "$k79out\$Name.err"
        if (!$proc.WaitForExit($TimeoutSeconds*1000)) { throw "$Name timed out" }
        $proc.WaitForExit()
        if ($proc.ExitCode -ne 0) { throw "$Name exit $($proc.ExitCode)" }
        return ((Get-Content "$k79out\$Name.out" -Raw)+(Get-Content "$k79out\$Name.err" -Raw))
    } finally {
        if ($proc) {
            if (!$proc.HasExited) { $proc.Kill(); $proc.WaitForExit() }
            $proc.Dispose()
        }
    }
}
$audit=Get-Content "$k79out\candidate-validation.json" -Raw | ConvertFrom-Json
$fw=Get-Content "$k79out\firmware-validation.json" -Raw | ConvertFrom-Json
if (!$audit.only_boot_update_required -or !$audit.kernel_image_config_and_logdump_unchanged -or !$audit.dtb_audit.only_gpi0_qup0_i2c1_enabled_and_400khz -or !$fw.other_executable_bytes_unchanged -or !$fw.firmware_dtb_raw_section_matches) {throw 'Candidate audit failed'}
if ((Get-FileHash "$k79out\boot-before.img").Hash.ToLowerInvariant() -ne '3fbbd0eecf7e793f97920d55bd9ec2a30329d6e53edb307200160a23e1de923e') {throw 'Boot rollback mismatch'}
if ((Get-FileHash "$k79out\logdump-before.img").Hash.ToLowerInvariant() -ne '607fc6b4b0caba8ca5c7ea6677fd8259c81a216f91b2d6de7603e3f56d9881d0') {throw 'Logdump baseline mismatch'}
$events=Get-Content "$k79out\bus-f1-wsl.events.jsonl" | ForEach-Object {$_ | ConvertFrom-Json}
if (!@($events | Where-Object {$_.event -eq 'receipt' -and $_.text -eq 'F1'}).Count) {throw 'No current F1 receipt'}
$usb=(& 'C:\Program Files\usbipd-win\usbipd.exe' list | Out-String)
if ($usb -match '(?m)^6-5\s+05c6:9505\s+[^\r\n]*Attached') {throw 'EUD still attached'}
$devices=''
for ($attempt=1; $attempt -le 10; $attempt++) {
    $devices=Invoke-K72Fastboot "bus-confirm-devices-$attempt" @('devices') 15
    if ($devices -match '(?im)^62bc28a1\s+fastboot\s*$') {break}
    Start-Sleep -Milliseconds 1000
}
if ($devices -notmatch '(?im)^62bc28a1\s+fastboot\s*$') {throw 'Phone not independently enumerated in fastboot'}
$product=Invoke-K72Fastboot 'bus-confirm-product' @('-s','62bc28a1','getvar','product') 15
if ($product -notmatch 'product:\s*msmnile') {throw 'Unexpected product'}
$size=Invoke-K72Fastboot 'bus-confirm-size-boot' @('-s','62bc28a1','getvar','partition-size:boot') 15
if ($size -notmatch 'partition-size:boot:\s*(0x[0-9a-fA-F]+)') {throw 'Partition size missing'}
$partitionBytes=[Convert]::ToInt64($Matches[1].Substring(2),16)
$image="$k79out\boot-k79-bus.img"
$hash=(Get-FileHash $image).Hash.ToLowerInvariant()
if ($partitionBytes -lt (Get-Item $image).Length -or $hash -ne '08edf9bcc1c55977169b0a8fd9f963805ba98d0423929e09e17bb9f811ca7405') {throw 'Image/partition/hash mismatch'}
$flash=Invoke-K72Fastboot 'bus-flash-boot' @('-s','62bc28a1','flash','boot',$image) 60
if ($flash -notmatch "Writing 'boot'\s+OKAY") {throw 'Successful write not observed'}
$flash
$reboot=Invoke-K72Fastboot 'bus-reboot' @('-s','62bc28a1','reboot') 15
[ordered]@{utc=[DateTime]::UtcNow.ToString('o');serial='62bc28a1';product='msmnile';flashed_partitions=@('boot');partition_bytes=$partitionBytes;image_sha256=$hash;flash_success=$true;reboot_success=$true;processes_disposed=$true;boot_written=$true;logdump_written=$false;userdata_written=$false;gpt_written=$false} | ConvertTo-Json -Depth 4 | Set-Content "$k79out\bus-flash-validation.json"
$reboot
