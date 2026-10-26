$ErrorActionPreference='Stop'
$out77='E:\edk2-samurai-out\kernel77'
$fastboot77='C:\Users\cy122\Downloads\platform-tools\platform-tools\fastboot.exe'
$events=Get-Content "$out77\recheck-f1-wsl.events.jsonl" | ForEach-Object {$_ | ConvertFrom-Json}
if (!@($events | Where-Object {$_.event -eq 'receipt' -and $_.text -eq 'F1'}).Count) {throw 'Fresh F1 receipt missing'}
function Invoke-RecheckFastboot([string]$Name,[string[]]$Arguments) {
    $proc=$null
    try {
        if (Test-Path -LiteralPath "$out77\$Name.out") {throw 'Use a fresh prefix'}
        $proc=Start-Process -FilePath $fastboot77 -ArgumentList $Arguments -WindowStyle Hidden -PassThru -RedirectStandardOutput "$out77\$Name.out" -RedirectStandardError "$out77\$Name.err"
        if (!$proc.WaitForExit(15000)) {throw 'Fastboot timed out'}
        $proc.WaitForExit()
        if ($proc.ExitCode -ne 0) {throw 'Fastboot failed'}
        return ((Get-Content "$out77\$Name.out" -Raw)+(Get-Content "$out77\$Name.err" -Raw))
    } finally {
        if ($proc) {
            if (!$proc.HasExited) {$proc.Kill();$proc.WaitForExit()}
            $proc.Dispose()
        }
    }
}
$devices=''
for ($attempt=1; $attempt -le 10; $attempt++) {
    $devices=Invoke-RecheckFastboot "recheck-devices-$attempt" @('devices')
    if ($devices -match '(?im)^62bc28a1\s+fastboot\s*$') {break}
    Start-Sleep -Milliseconds 1000
}
if ($devices -notmatch '(?im)^62bc28a1\s+fastboot\s*$') {throw 'Expected serial not in fastboot'}
$product=Invoke-RecheckFastboot 'recheck-product' @('-s','62bc28a1','getvar','product')
if ($product -notmatch 'product:\s*msmnile') {throw 'Unexpected product'}
Invoke-RecheckFastboot 'recheck-reboot' @('-s','62bc28a1','reboot')
[ordered]@{serial='62bc28a1';product='msmnile';boot_written=$false;logdump_written=$false;reboot_success=$true;processes_disposed=$true} | ConvertTo-Json | Set-Content "$out77\recheck-reboot.json"
