param([Parameter(Mandatory)][ValidatePattern('^[a-z0-9-]+$')][string]$Prefix)
$ErrorActionPreference='Stop'
$out='E:\edk2-samurai-out\kernel109'
$fb='C:\Users\cy122\Downloads\platform-tools\platform-tools\fastboot.exe'
$serial=(Get-Content -LiteralPath "$out\fastboot-identity.json" -Raw | ConvertFrom-Json).serial
if ($serial -notmatch '^[a-z0-9]{8}$') {throw 'Verified identity unavailable'}
$events=Get-Content -LiteralPath "$out\$Prefix-f1-wsl.events.jsonl" | ForEach-Object {$_ | ConvertFrom-Json}
if (!@($events | Where-Object {$_.event -eq 'receipt' -and $_.text -eq 'F1'}).Count) {throw 'F1 receipt missing'}
function Invoke-Fb([string]$name,[string[]]$arguments) {
    $process=$null
    try {
        if (Test-Path -LiteralPath "$out\$Prefix-$name.out") {throw 'Use a fresh output prefix'}
        $process=Start-Process -FilePath $fb -ArgumentList $arguments -WindowStyle Hidden -PassThru -RedirectStandardOutput "$out\$Prefix-$name.out" -RedirectStandardError "$out\$Prefix-$name.err"
        if (!$process.WaitForExit(15000)) {throw 'Fastboot operation timed out'}
        $process.WaitForExit()
        if ($process.ExitCode -ne 0) {throw 'Fastboot operation failed'}
        return ((Get-Content -LiteralPath "$out\$Prefix-$name.out" -Raw)+(Get-Content -LiteralPath "$out\$Prefix-$name.err" -Raw))
    } finally {
        if ($process) {if (!$process.HasExited) {$process.Kill();$process.WaitForExit()};$process.Dispose()}
    }
}
$devices=Invoke-Fb 'devices' @('devices')
if ($devices -notmatch ('(?im)^'+[regex]::Escape($serial)+'\s+fastboot\s*$')) {throw 'Independent fastboot enumeration failed'}
$product=Invoke-Fb 'product' @('-s',$serial,'getvar','product')
if ($product -notmatch 'product:\s*msmnile') {throw 'Unexpected product'}
$null=Invoke-Fb 'reboot' @('-s',$serial,'reboot')
[ordered]@{recovery_reboot_only=$true;partitions_flashed=@();utc=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content -Encoding utf8NoBOM "$out\$Prefix-reboot-validation.json"
Write-Output 'VERIFIED_FASTBOOT_REBOOT_ONLY_COMPLETE'
