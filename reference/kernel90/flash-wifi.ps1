$ErrorActionPreference='Stop'
$k90fb='C:\Users\cy122\Downloads\platform-tools\platform-tools\fastboot.exe'
$k90out='E:\edk2-samurai-out\kernel90'
function Invoke-K89Fastboot([string]$Name,[string[]]$Arguments,[int]$TimeoutSeconds) {
    $proc=$null
    try {
        if (Test-Path -LiteralPath "$k90out\$Name.out") { throw 'Use a new output prefix' }
        $proc=Start-Process -FilePath $k90fb -ArgumentList $Arguments -WindowStyle Hidden -PassThru -RedirectStandardOutput "$k90out\$Name.out" -RedirectStandardError "$k90out\$Name.err"
        if (!$proc.WaitForExit($TimeoutSeconds*1000)) { throw "$Name timed out" }
        $proc.WaitForExit()
        if ($proc.ExitCode -ne 0) { throw "$Name exit $($proc.ExitCode)" }
        return ((Get-Content "$k90out\$Name.out" -Raw)+(Get-Content "$k90out\$Name.err" -Raw))
    } finally {
        if ($proc) {
            if (!$proc.HasExited) { $proc.Kill(); $proc.WaitForExit() }
            $proc.Dispose()
        }
    }
}
$audit=Get-Content "$k90out\candidate-validation.json" -Raw | ConvertFrom-Json
if (!$audit.candidate_audit_pass -or !$audit.firmware_audit_pass -or !$audit.initramfs_byte_identical -or !$audit.snapshot_preserved) {throw 'Candidate audit failed'}
foreach ($entry in @(@('boot-before.img',$audit.full_backup_boot_sha256),@('logdump-before.img',$audit.full_backup_logdump_sha256))) {
    if ((Get-FileHash "$k90out\$($entry[0])").Hash.ToLowerInvariant() -ne $entry[1]) {throw 'Rollback hash mismatch'}
}
$guard=Get-Content "$k90out\guard-before-flash.txt" -Raw
if (!$guard.StartsWith('f3c087f8-e9d3-491f-b5ad-c5511082fe29') -or $guard -notmatch '251913dbdb6c63a73e2bce75c12b7242e0f0e4cfc1a64a7c28463b2769865075' -or $guard -notmatch '73c7154f3f221c906a49d8077ae98ca5a08fabf3a9bf29ba2c68615d496b5675') {throw 'Fresh live guard missing'}
$events=Get-Content "$k90out\wifi-f1-wsl.events.jsonl" | ForEach-Object {$_ | ConvertFrom-Json}
if (!@($events | Where-Object {$_.event -eq 'receipt' -and $_.text -eq 'F1'}).Count) {throw 'No current F1 receipt'}
$usb=(& 'C:\Program Files\usbipd-win\usbipd.exe' list | Out-String)
if ($usb -match '(?m)^6-5\s+05c6:9505\s+[^\r\n]*Attached') {throw 'EUD still attached'}
$devices=Invoke-K89Fastboot 'confirm-devices' @('devices') 15
if ($devices -notmatch '(?im)^62bc28a1\s+fastboot\s*$') {throw 'Phone not independently enumerated in fastboot'}
$product=Invoke-K89Fastboot 'confirm-product' @('-s','62bc28a1','getvar','product') 15
if ($product -notmatch 'product:\s*msmnile') {throw 'Unexpected product'}
# Validate BOTH partitions and candidates before the first write.
foreach ($part in @('boot')) {
    $size=Invoke-K89Fastboot "confirm-size-$part" @('-s','62bc28a1','getvar',"partition-size:$part") 15
    if ($size -notmatch "partition-size:${part}:\s*(0x[0-9a-fA-F]+)") {throw 'Partition size missing'}
    $bytes=[Convert]::ToInt64($Matches[1].Substring(2),16)
    $expected=if ($part -eq 'boot') {100663296} else {67108864}
    if ($bytes -ne $expected) {throw 'Partition size mismatch'}
    $image=if ($part -eq 'boot') {"$k90out\boot-k90-wifi.img"} else {"$k90out\logdump-k90-mpss.img"}
    $hash=if ($part -eq 'boot') {$audit.boot_sha256} else {$audit.logdump_sha256}
    if ((Get-Item $image).Length -gt $bytes -or (Get-FileHash $image).Hash.ToLowerInvariant() -ne $hash) {throw 'Candidate size/hash mismatch'}
}
foreach ($part in @('boot')) {
    $image=if ($part -eq 'boot') {"$k90out\boot-k90-wifi.img"} else {"$k90out\logdump-k90-mpss.img"}
    $result=Invoke-K89Fastboot "flash-$part" @('-s','62bc28a1','flash',$part,$image) 60
    if ($result -notmatch "Writing '$part'\s+OKAY") {throw 'Successful write not observed'}
    $result
}
Invoke-K89Fastboot 'reboot' @('-s','62bc28a1','reboot') 15
[ordered]@{utc=[DateTime]::UtcNow.ToString('o');serial='62bc28a1';product='msmnile';flashed_partitions=@('boot');boot_sha256=$audit.boot_sha256;logdump_sha256=$audit.logdump_sha256;flash_success=$true;reboot_success=$true;processes_disposed=$true} | ConvertTo-Json | Set-Content "$k90out\flash-validation.json"

