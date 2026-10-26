$ErrorActionPreference='Stop'
$k92fb='C:\Users\cy122\Downloads\platform-tools\platform-tools\fastboot.exe'
$k92out='E:\edk2-samurai-out\kernel92'
function Invoke-K92Fastboot([string]$Name,[string[]]$Arguments,[int]$TimeoutSeconds) {
    $proc=$null
    try {
        if (Test-Path -LiteralPath "$k92out\$Name.out") { throw 'Use a new output prefix' }
        $proc=Start-Process -FilePath $k92fb -ArgumentList $Arguments -WindowStyle Hidden -PassThru -RedirectStandardOutput "$k92out\$Name.out" -RedirectStandardError "$k92out\$Name.err"
        if (!$proc.WaitForExit($TimeoutSeconds*1000)) { throw "$Name timed out" }
        $proc.WaitForExit()
        if ($proc.ExitCode -ne 0) { throw "$Name exit $($proc.ExitCode)" }
        return ((Get-Content "$k92out\$Name.out" -Raw)+(Get-Content "$k92out\$Name.err" -Raw))
    } finally {
        if ($proc) {
            if (!$proc.HasExited) { $proc.Kill(); $proc.WaitForExit() }
            $proc.Dispose()
        }
    }
}
$audit=Get-Content "$k92out\candidate-validation.json" -Raw | ConvertFrom-Json
if (!$audit.candidate_audit_pass -or !$audit.firmware_audit_pass -or !$audit.original_initramfs_files_preserved -or !$audit.earlier_snapshots_preserved -or $audit.embedded_wifi_credentials -or $audit.nv_partition_writes -or $audit.kernel_build -ne 91) {throw 'Candidate audit failed'}
if (($audit.only_flash_partitions -join ',') -ne 'logdump,boot') {throw 'Unexpected flash scope'}
$k92live="$k92out\live-preflash\k92-live-preflash"
foreach ($line in Get-Content "$k92live\SHA256SUMS") {
    $hash,$name=$line -split '  ',2
    if ((Get-FileHash -LiteralPath "$k92live\$name").Hash.ToLowerInvariant() -ne $hash) {throw 'Fresh snapshot hash mismatch'}
}
foreach ($entry in @(@('boot-partition-before.img',$audit.full_backup_boot_sha256),@('logdump-before.img',$audit.full_backup_logdump_sha256))) {
    if ((Get-FileHash "$k92out\$($entry[0])").Hash.ToLowerInvariant() -ne $entry[1] -or (Get-FileHash "$k92live\$($entry[0])").Hash.ToLowerInvariant() -ne $entry[1]) {throw 'Rollback hash mismatch'}
}
$guard=Get-Content "$k92live\guard.txt" -Raw
if (!$guard.StartsWith("e0b67ee9-b16d-49f7-9ffd-f0bcfca87496`noffline`n") -or $guard -notmatch 'ed7ba3a76892fa2dd276daef3bc66c14c0737f49d385ae840a397fdfae39e396' -or $guard -notmatch '37ea81b0c2dbc678ed090048fcad8160acd089f1b7189eddbf0d0c873698ac36') {throw 'Fresh live guard missing'}
$events=Get-Content "$k92out\connectivity-f1-wsl.events.jsonl" | ForEach-Object {$_ | ConvertFrom-Json}
if (!@($events | Where-Object {$_.event -eq 'receipt' -and $_.text -eq 'F1'}).Count) {throw 'No current F1 receipt'}
$usb=(& 'C:\Program Files\usbipd-win\usbipd.exe' list | Out-String)
if ($usb -match '(?m)^6-5\s+05c6:9505\s+[^\r\n]*Attached') {throw 'EUD still attached'}
$devices=Invoke-K92Fastboot 'confirm-devices' @('devices') 15
if ($devices -notmatch '(?im)^62bc28a1\s+fastboot\s*$') {throw 'Phone not independently enumerated in fastboot'}
$product=Invoke-K92Fastboot 'confirm-product' @('-s','62bc28a1','getvar','product') 15
if ($product -notmatch 'product:\s*msmnile') {throw 'Unexpected product'}
# Validate BOTH partitions and candidates before the first write.
foreach ($part in @('boot','logdump')) {
    $size=Invoke-K92Fastboot "confirm-size-$part" @('-s','62bc28a1','getvar',"partition-size:$part") 15
    if ($size -notmatch "partition-size:${part}:\s*(0x[0-9a-fA-F]+)") {throw 'Partition size missing'}
    $bytes=[Convert]::ToInt64($Matches[1].Substring(2),16)
    $expected=if ($part -eq 'boot') {100663296} else {67108864}
    if ($bytes -ne $expected) {throw 'Partition size mismatch'}
    $image=if ($part -eq 'boot') {"$k92out\boot-k92-connectivity.img"} else {"$k92out\logdump-k92-connectivity.img"}
    $hash=if ($part -eq 'boot') {$audit.boot_sha256} else {$audit.logdump_sha256}
    if ((Get-Item $image).Length -gt $bytes -or (Get-FileHash $image).Hash.ToLowerInvariant() -ne $hash) {throw 'Candidate size/hash mismatch'}
}
foreach ($part in @('logdump','boot')) {
    $image=if ($part -eq 'boot') {"$k92out\boot-k92-connectivity.img"} else {"$k92out\logdump-k92-connectivity.img"}
    $result=Invoke-K92Fastboot "flash-$part" @('-s','62bc28a1','flash',$part,$image) 60
    if ($result -notmatch "Writing '$part'\s+OKAY") {throw 'Successful write not observed'}
    $result
}
Invoke-K92Fastboot 'reboot' @('-s','62bc28a1','reboot') 15
[ordered]@{utc=[DateTime]::UtcNow.ToString('o');serial='62bc28a1';product='msmnile';flashed_partitions=@('logdump','boot');boot_sha256=$audit.boot_sha256;logdump_sha256=$audit.logdump_sha256;flash_success=$true;reboot_success=$true;processes_disposed=$true} | ConvertTo-Json | Set-Content "$k92out\flash-validation.json"
