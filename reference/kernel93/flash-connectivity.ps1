param([ValidatePattern('^[a-z0-9-]+$')][string]$Attempt='retry1')
$ErrorActionPreference='Stop'
$k93fb='C:\Users\cy122\Downloads\platform-tools\platform-tools\fastboot.exe'
$k93out='E:\edk2-samurai-out\kernel93'
function Invoke-K93Fastboot([string]$Name,[string[]]$Arguments,[int]$TimeoutSeconds) {
    $Name="$Attempt-$Name"
    $proc=$null
    try {
        if (Test-Path -LiteralPath "$k93out\$Name.out") { throw 'Use a new output prefix' }
        $proc=Start-Process -FilePath $k93fb -ArgumentList $Arguments -WindowStyle Hidden -PassThru -RedirectStandardOutput "$k93out\$Name.out" -RedirectStandardError "$k93out\$Name.err"
        if (!$proc.WaitForExit($TimeoutSeconds*1000)) { throw "$Name timed out" }
        $proc.WaitForExit()
        if ($proc.ExitCode -ne 0) { throw "$Name exit $($proc.ExitCode)" }
        return ((Get-Content "$k93out\$Name.out" -Raw)+(Get-Content "$k93out\$Name.err" -Raw))
    } finally {
        if ($proc) {
            if (!$proc.HasExited) { $proc.Kill(); $proc.WaitForExit() }
            $proc.Dispose()
        }
    }
}
$audit=Get-Content "$k93out\candidate-validation.json" -Raw | ConvertFrom-Json
if (!$audit.candidate_audit_pass -or !$audit.firmware_audit_pass -or !$audit.original_initramfs_files_preserved -or !$audit.earlier_snapshots_preserved -or $audit.embedded_wifi_credentials -or $audit.nv_partition_writes -or $audit.kernel_build -ne 92) {throw 'Candidate audit failed'}
if (($audit.only_flash_partitions -join ',') -ne 'logdump,boot') {throw 'Unexpected flash scope'}
if ((Get-FileHash "$k93out\preflash.tar").Hash.ToLowerInvariant() -ne 'b16c67e7ed39f52a6d26989b02fda54a142becc6a75bb74cd43dd43e0e40d9c3') {throw 'Fresh snapshot hash mismatch'}
foreach ($entry in @(@('boot-partition-before.img',$audit.full_backup_boot_sha256),@('logdump-before.img',$audit.full_backup_logdump_sha256))) {
    if ((Get-FileHash "$k93out\$($entry[0])").Hash.ToLowerInvariant() -ne $entry[1]) {throw 'Rollback hash mismatch'}
}
$guard=Get-Content "$k93out\guard-before-flash.txt" -Raw
if (!$guard.StartsWith("7198e2c9-17e4-42af-ac12-71a2013b5ea8`n") -or $guard -notmatch 'cd75317e7384dd65463982134fd9a9ffdd35cb1f21f06a337824683c18636f48' -or $guard -notmatch '7972dae9d5f3c709fd41f8b0e577417e1f6278930afa04762bae70dbb85ace86') {throw 'Fresh live guard missing'}
$stop=Get-Content "$k93out\stop-connectivity.log" -Raw
if ($stop -notmatch 'CONNECTIVITY_STOPPED' -or $stop -notmatch '7198e2c9-17e4-42af-ac12-71a2013b5ea8') {throw 'Controlled stop evidence missing'}
$events=Get-Content "$k93out\connectivity-f1-wsl.events.jsonl" | ForEach-Object {$_ | ConvertFrom-Json}
if (!@($events | Where-Object {$_.event -eq 'receipt' -and $_.text -eq 'F1'}).Count) {throw 'No current F1 receipt'}
$usb=(& 'C:\Program Files\usbipd-win\usbipd.exe' list | Out-String)
if ($usb -match '(?m)^6-5\s+05c6:9505\s+[^\r\n]*Attached') {throw 'EUD still attached'}
$devices=Invoke-K93Fastboot 'confirm-devices' @('devices') 15
if ($devices -notmatch '(?im)^62bc28a1\s+fastboot\s*$') {throw 'Phone not independently enumerated in fastboot'}
$product=Invoke-K93Fastboot 'confirm-product' @('-s','62bc28a1','getvar','product') 15
if ($product -notmatch 'product:\s*msmnile') {throw 'Unexpected product'}
# Validate BOTH partitions and candidates before the first write.
foreach ($part in @('boot','logdump')) {
    $size=Invoke-K93Fastboot "confirm-size-$part" @('-s','62bc28a1','getvar',"partition-size:$part") 15
    if ($size -notmatch "partition-size:${part}:\s*(0x[0-9a-fA-F]+)") {throw 'Partition size missing'}
    $bytes=[Convert]::ToInt64($Matches[1].Substring(2),16)
    $expected=if ($part -eq 'boot') {100663296} else {67108864}
    if ($bytes -ne $expected) {throw 'Partition size mismatch'}
    $image=if ($part -eq 'boot') {"$k93out\boot-k93-connectivity.img"} else {"$k93out\logdump-k93-connectivity.img"}
    $hash=if ($part -eq 'boot') {$audit.boot_sha256} else {$audit.logdump_sha256}
    if ((Get-Item $image).Length -gt $bytes -or (Get-FileHash $image).Hash.ToLowerInvariant() -ne $hash) {throw 'Candidate size/hash mismatch'}
}
foreach ($part in @('logdump','boot')) {
    $image=if ($part -eq 'boot') {"$k93out\boot-k93-connectivity.img"} else {"$k93out\logdump-k93-connectivity.img"}
    $result=Invoke-K93Fastboot "flash-$part" @('-s','62bc28a1','flash',$part,$image) 60
    if ($result -notmatch "Writing '$part'\s+OKAY") {throw 'Successful write not observed'}
    $result
}
Invoke-K93Fastboot 'reboot' @('-s','62bc28a1','reboot') 15
[ordered]@{utc=[DateTime]::UtcNow.ToString('o');serial='62bc28a1';product='msmnile';flashed_partitions=@('logdump','boot');boot_sha256=$audit.boot_sha256;logdump_sha256=$audit.logdump_sha256;flash_success=$true;reboot_success=$true;processes_disposed=$true} | ConvertTo-Json | Set-Content "$k93out\flash-validation.json"
