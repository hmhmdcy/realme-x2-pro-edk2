param([ValidatePattern('^[a-z0-9-]+$')][string]$Attempt='first')
$ErrorActionPreference='Stop'
$k102fb='C:\Users\cy122\Downloads\platform-tools\platform-tools\fastboot.exe'
$k102out='E:\edk2-samurai-out\kernel102'
$k102serial=(Get-Content ($k102out+'\fastboot-identity.json') -Raw | ConvertFrom-Json).serial
if ($k102serial -notmatch '^[a-z0-9]{8}$') {throw 'Private verified serial missing'}
function Invoke-K102Fastboot([string]$Name,[string[]]$Arguments,[int]$TimeoutSeconds) {
    $Name="$Attempt-$Name"
    $proc=$null
    try {
        if (Test-Path -LiteralPath "$k102out\$Name.out") {throw 'Use a new output prefix'}
        $proc=Start-Process -FilePath $k102fb -ArgumentList $Arguments -WindowStyle Hidden -PassThru -RedirectStandardOutput "$k102out\$Name.out" -RedirectStandardError "$k102out\$Name.err"
        if (!$proc.WaitForExit($TimeoutSeconds*1000)) {throw "$Name timed out"}
        $proc.WaitForExit()
        if ($proc.ExitCode -ne 0) {throw "$Name exit $($proc.ExitCode)"}
        return ((Get-Content "$k102out\$Name.out" -Raw)+(Get-Content "$k102out\$Name.err" -Raw))
    } finally {
        if ($proc) {
            if (!$proc.HasExited) {$proc.Kill();$proc.WaitForExit()}
            $proc.Dispose()
        }
    }
}
$audit=Get-Content "$k102out\candidate-validation.json" -Raw | ConvertFrom-Json
if (!$audit.candidate_audit_pass -or !$audit.original_initramfs_files_preserved -or !$audit.earlier_snapshots_preserved -or !$audit.firmware_dtb_raw_section_matches -or !$audit.other_executable_bytes_unchanged -or $audit.embedded_wifi_credentials -or $audit.embedded_device_addresses -or $audit.nv_partition_writes -or $audit.kernel_build -ne 101) {throw 'Candidate audit failed'}
if (($audit.only_flash_partitions -join ',') -ne 'boot,logdump') {throw 'Unexpected flash scope'}
if ((Get-FileHash "$k102out\preflash.tar").Hash.ToLowerInvariant() -ne $audit.preflash_sha256) {throw 'Fresh snapshot hash mismatch'}
foreach ($entry in @(@('boot-partition-before.img',$audit.full_backup_boot_sha256),@('logdump-before.img',$audit.full_backup_logdump_sha256))) {
    if ((Get-FileHash "$k102out\$($entry[0])").Hash.ToLowerInvariant() -ne $entry[1]) {throw 'Rollback hash mismatch'}
}
$guard=Get-Content "$k102out\guard-before-flash.txt" -Raw
if (!$guard.StartsWith(($audit.before_boot_id+"`n")) -or $guard -notmatch $audit.full_backup_boot_sha256 -or $guard -notmatch $audit.full_backup_logdump_sha256) {throw 'Fresh live guard missing'}
$stop=Get-Content "$k102out\stop-connectivity-final.log" -Raw
if ($stop -notmatch 'CONNECTIVITY_STOPPED' -or $stop -notmatch [regex]::Escape($audit.before_boot_id)) {throw 'Controlled stop evidence missing'}
$events=Get-Content "$k102out\connectivity-f1-wsl.events.jsonl" | ForEach-Object {$_ | ConvertFrom-Json}
if (!@($events | Where-Object {$_.event -eq 'receipt' -and $_.text -eq 'F1'}).Count) {throw 'No current F1 receipt'}
$usb=(& 'C:\Program Files\usbipd-win\usbipd.exe' list | Out-String)
if ($usb -match '(?m)^6-5\s+05c6:9505\s+[^\r\n]*Attached') {throw 'EUD still attached'}
$devices=Invoke-K102Fastboot 'confirm-devices' @('devices') 15
if ($devices -notmatch ('(?im)^'+[regex]::Escape($k102serial)+'\s+fastboot\s*$')) {throw 'Phone not independently enumerated in fastboot'}
$product=Invoke-K102Fastboot 'confirm-product' @('-s',$k102serial,'getvar','product') 15
if ($product -notmatch 'product:\s*msmnile') {throw 'Unexpected product'}
$size=Invoke-K102Fastboot 'confirm-size-logdump' @('-s',$k102serial,'getvar','partition-size:logdump') 15
if ($size -notmatch 'partition-size:logdump:\s*(0x[0-9a-fA-F]+)') {throw 'Partition size missing'}
$bytes=[Convert]::ToInt64($Matches[1].Substring(2),16)
if ($bytes -ne 67108864) {throw 'Partition size mismatch'}
$image="$k102out\logdump-k102-audio.img"
if ((Get-Item $image).Length -ne $bytes -or (Get-FileHash $image).Hash.ToLowerInvariant() -ne $audit.logdump_sha256) {throw 'Candidate size/hash mismatch'}
$bootSize=Invoke-K102Fastboot 'confirm-size-boot' @('-s',$k102serial,'getvar','partition-size:boot') 15
if ($bootSize -notmatch 'partition-size:boot:\s*(0x[0-9a-fA-F]+)') {throw 'Boot partition size missing'}
if ([Convert]::ToInt64($Matches[1].Substring(2),16) -ne 100663296) {throw 'Boot partition size mismatch'}
$bootImage="$k102out\boot-k102-audio.img"
if ((Get-Item $bootImage).Length -ne $audit.boot_bytes -or (Get-Item $bootImage).Length -gt 100663296 -or (Get-FileHash $bootImage).Hash.ToLowerInvariant() -ne $audit.boot_sha256) {throw 'Firmware boot size/hash mismatch'}
$bootResult=Invoke-K102Fastboot 'flash-boot' @('-s',$k102serial,'flash','boot',$bootImage) 60
if ($bootResult -notmatch "Writing 'boot'\s+OKAY") {throw 'Successful boot write not observed'}
$bootResult
$result=Invoke-K102Fastboot 'flash-logdump' @('-s',$k102serial,'flash','logdump',$image) 60
if ($result -notmatch "Writing 'logdump'\s+OKAY") {throw 'Successful write not observed'}
$result
Invoke-K102Fastboot 'reboot' @('-s',$k102serial,'reboot') 15
[ordered]@{utc=[DateTime]::UtcNow.ToString('o');flashed_partitions=@('boot','logdump');firmware_dtb_rebuilt=$true;boot_sha256=$audit.boot_sha256;logdump_sha256=$audit.logdump_sha256;flash_success=$true;reboot_success=$true;processes_disposed=$true} | ConvertTo-Json | Set-Content "$k102out\flash-validation.json"
