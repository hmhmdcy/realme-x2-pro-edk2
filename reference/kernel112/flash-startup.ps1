param([ValidatePattern('^[a-z0-9-]+$')][string]$Prefix='startup-first')
$ErrorActionPreference='Stop'
$out='E:\edk2-samurai-out\kernel112'
$fb='C:\Users\cy122\Downloads\platform-tools\platform-tools\fastboot.exe'
$serial=(Get-Content -LiteralPath 'E:\edk2-samurai-out\kernel109\fastboot-identity.json' -Raw | ConvertFrom-Json).serial
if ($serial -notmatch '^[a-z0-9]{8}$') {throw 'Verified identity missing'}
$a=Get-Content -LiteralPath "$out\candidate-validation.json" -Raw | ConvertFrom-Json
if (!$a.candidate_audit_pass -or $a.kernel_build -ne 112 -or !$a.dtb_byte_identical -or !$a.boot_firmware_unchanged -or $a.userdata_reformatted -or ($a.flash_partitions -join ',') -ne 'logdump' -or $a.slpi_auto_boot) {throw 'Candidate scope rejected'}
foreach ($item in @(@('logdump-before.img',$a.before_logdump_sha256),@('logdump-k112-startup.img',$a.logdump_sha256))) {
    if ((Get-FileHash -LiteralPath "$out\$($item[0])").Hash.ToLowerInvariant() -ne $item[1]) {throw 'Candidate/rollback bytes changed'}
}
if ((Get-Content -LiteralPath "$out\$Prefix-quiesce.out" -Raw) -notmatch 'KERNEL112_DIAGNOSTIC_ROOT_NO_BLOCK_MOUNTS_REBOOT_READY') {throw 'Current diagnostic root checkpoint missing'}
$events=Get-Content -LiteralPath "$out\$Prefix-f1-wsl.events.jsonl" | ForEach-Object {$_ | ConvertFrom-Json}
if (!@($events | Where-Object {$_.event -eq 'receipt' -and $_.text -eq 'F1'}).Count) {throw 'Fresh F1 receipt missing'}
function Invoke-Fb([string]$name,[string[]]$arguments,[int]$seconds=15) {
    $p=$null;$base="$out\$Prefix-$name"
    if (Test-Path -LiteralPath "$base.out") {throw 'Fresh flash prefix required'}
    try {
        $p=Start-Process -FilePath $fb -ArgumentList $arguments -WindowStyle Hidden -PassThru -RedirectStandardOutput "$base.out" -RedirectStandardError "$base.err"
        if (!$p.WaitForExit($seconds*1000)) {throw 'Fastboot timed out'}
        $p.WaitForExit();if ($p.ExitCode -ne 0) {throw "Fastboot $name failed"}
        return ((Get-Content -LiteralPath "$base.out" -Raw)+(Get-Content -LiteralPath "$base.err" -Raw))
    } finally {if ($p) {if (!$p.HasExited) {$p.Kill();$p.WaitForExit()};$p.Dispose()}}
}
$devices=Invoke-Fb 'devices' @('devices')
if ($devices -notmatch ('(?im)^'+[regex]::Escape($serial)+'\s+fastboot\s*$')) {throw 'Independent enumeration failed'}
$product=Invoke-Fb 'product' @('-s',$serial,'getvar','product')
if ($product -notmatch 'product:\s*msmnile') {throw 'Unexpected product'}
$size=Invoke-Fb 'size-logdump' @('-s',$serial,'getvar','partition-size:logdump')
if ($size -notmatch 'partition-size:logdump:\s*(0x[0-9a-fA-F]+)' -or [Convert]::ToInt64($Matches[1].Substring(2),16) -ne 67108864) {throw 'Partition geometry changed'}
$image="$out\logdump-k112-startup.img"
if ((Get-Item -LiteralPath $image).Length -ne 67108864) {throw 'Image length changed'}
$r=Invoke-Fb 'flash-logdump' @('-s',$serial,'flash','logdump',$image) 90
if ($r -notmatch "Writing 'logdump'\s+OKAY" -or $r -match 'FAILED') {throw 'Write receipt missing'}
$null=Invoke-Fb 'reboot' @('-s',$serial,'reboot')
[ordered]@{flash_success=$true;kernel_build=112;partitions=@('logdump');userdata_erased=$false;boot_sha256=$a.boot_sha256;logdump_sha256=$a.logdump_sha256;slpi_auto_boot=$false;hardware_test_pending=$true} | ConvertTo-Json | Set-Content -LiteralPath "$out\$Prefix-flash-validation.json" -Encoding utf8NoBOM
Write-Output 'KERNEL112_LOGDUMP_FLASH_AND_REBOOT_COMPLETE'
