param([ValidatePattern('^[a-z0-9-]+$')][string]$Attempt='first')
$ErrorActionPreference='Stop'
$k94fb='C:\Users\cy122\Downloads\platform-tools\platform-tools\fastboot.exe'
$k94out='E:\edk2-samurai-out\kernel94'
$k94serial=(Get-Content ($k94out+'\fastboot-identity.json') -Raw | ConvertFrom-Json).serial
if ($k94serial -notmatch '^[a-z0-9]{8}$') {throw 'Private verified serial missing'}
function Invoke-K94Fastboot([string]$Name,[string[]]$Arguments,[int]$TimeoutSeconds) {
    $Name="$Attempt-$Name"
    $proc=$null
    try {
        if (Test-Path -LiteralPath "$k94out\$Name.out") {throw 'Use a new output prefix'}
        $proc=Start-Process -FilePath $k94fb -ArgumentList $Arguments -WindowStyle Hidden -PassThru -RedirectStandardOutput "$k94out\$Name.out" -RedirectStandardError "$k94out\$Name.err"
        if (!$proc.WaitForExit($TimeoutSeconds*1000)) {throw "$Name timed out"}
        $proc.WaitForExit()
        if ($proc.ExitCode -ne 0) {throw "$Name exit $($proc.ExitCode)"}
        return ((Get-Content "$k94out\$Name.out" -Raw)+(Get-Content "$k94out\$Name.err" -Raw))
    } finally {
        if ($proc) {
            if (!$proc.HasExited) {$proc.Kill();$proc.WaitForExit()}
            $proc.Dispose()
        }
    }
}
$audit=Get-Content "$k94out\candidate-validation.json" -Raw | ConvertFrom-Json
if (!$audit.candidate_audit_pass -or !$audit.original_initramfs_files_preserved -or !$audit.earlier_snapshots_preserved -or !$audit.dtb_byte_identical -or !$audit.firmware_boot_reused_byte_identical -or $audit.embedded_wifi_credentials -or $audit.nv_partition_writes -or $audit.kernel_build -ne 93) {throw 'Candidate audit failed'}
if (($audit.only_flash_partitions -join ',') -ne 'logdump') {throw 'Unexpected flash scope'}
if ((Get-FileHash "$k94out\preflash.tar").Hash.ToLowerInvariant() -ne $audit.preflash_sha256) {throw 'Fresh snapshot hash mismatch'}
foreach ($entry in @(@('boot-partition-before.img',$audit.full_backup_boot_sha256),@('logdump-before.img',$audit.full_backup_logdump_sha256))) {
    if ((Get-FileHash "$k94out\$($entry[0])").Hash.ToLowerInvariant() -ne $entry[1]) {throw 'Rollback hash mismatch'}
}
$guard=Get-Content "$k94out\guard-before-flash.txt" -Raw
if (!$guard.StartsWith("b65a234f-44f4-4ad3-9d40-ecafdeb233b1`n") -or $guard -notmatch $audit.full_backup_boot_sha256 -or $guard -notmatch $audit.full_backup_logdump_sha256) {throw 'Fresh live guard missing'}
$stop=Get-Content "$k94out\stop-connectivity.log" -Raw
if ($stop -notmatch 'CONNECTIVITY_STOPPED' -or $stop -notmatch 'b65a234f-44f4-4ad3-9d40-ecafdeb233b1') {throw 'Controlled stop evidence missing'}
$events=Get-Content "$k94out\connectivity-f1-wsl.events.jsonl" | ForEach-Object {$_ | ConvertFrom-Json}
if (!@($events | Where-Object {$_.event -eq 'receipt' -and $_.text -eq 'F1'}).Count) {throw 'No current F1 receipt'}
$usb=(& 'C:\Program Files\usbipd-win\usbipd.exe' list | Out-String)
if ($usb -match '(?m)^6-5\s+05c6:9505\s+[^\r\n]*Attached') {throw 'EUD still attached'}
$devices=Invoke-K94Fastboot 'confirm-devices' @('devices') 15
if ($devices -notmatch ('(?im)^'+[regex]::Escape($k94serial)+'\s+fastboot\s*$')) {throw 'Phone not independently enumerated in fastboot'}
$product=Invoke-K94Fastboot 'confirm-product' @('-s',$k94serial,'getvar','product') 15
if ($product -notmatch 'product:\s*msmnile') {throw 'Unexpected product'}
$size=Invoke-K94Fastboot 'confirm-size-logdump' @('-s',$k94serial,'getvar','partition-size:logdump') 15
if ($size -notmatch 'partition-size:logdump:\s*(0x[0-9a-fA-F]+)') {throw 'Partition size missing'}
$bytes=[Convert]::ToInt64($Matches[1].Substring(2),16)
if ($bytes -ne 67108864) {throw 'Partition size mismatch'}
$image="$k94out\logdump-k94-connectivity.img"
if ((Get-Item $image).Length -ne $bytes -or (Get-FileHash $image).Hash.ToLowerInvariant() -ne $audit.logdump_sha256) {throw 'Candidate size/hash mismatch'}
$result=Invoke-K94Fastboot 'flash-logdump' @('-s',$k94serial,'flash','logdump',$image) 60
if ($result -notmatch "Writing 'logdump'\s+OKAY") {throw 'Successful write not observed'}
$result
Invoke-K94Fastboot 'reboot' @('-s',$k94serial,'reboot') 15
[ordered]@{utc=[DateTime]::UtcNow.ToString('o');flashed_partitions=@('logdump');boot_reused=$true;boot_sha256=$audit.boot_sha256;logdump_sha256=$audit.logdump_sha256;flash_success=$true;reboot_success=$true;processes_disposed=$true} | ConvertTo-Json | Set-Content "$k94out\flash-validation.json"
