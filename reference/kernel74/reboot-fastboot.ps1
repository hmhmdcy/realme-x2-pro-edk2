param([Parameter(Mandatory)][ValidatePattern('^[a-z0-9-]+$')][string]$Prefix)
$ErrorActionPreference='Stop'
$out='E:\edk2-samurai-out\kernel74'
$fb='C:\Users\cy122\Downloads\platform-tools\platform-tools\fastboot.exe'
function Invoke-RebootFastboot([string]$Name,[string[]]$Arguments) {
    $proc=$null
    try {
        if (Test-Path "$out\$Prefix-$Name.out") {throw 'Output prefix exists'}
        $proc=Start-Process -FilePath $fb -ArgumentList $Arguments -WindowStyle Hidden -PassThru -RedirectStandardOutput "$out\$Prefix-$Name.out" -RedirectStandardError "$out\$Prefix-$Name.err"
        if (!$proc.WaitForExit(15000)) {throw "$Name timed out"}
        $proc.WaitForExit()
        if ($proc.ExitCode -ne 0) {throw "$Name failed"}
        return ((Get-Content "$out\$Prefix-$Name.out" -Raw)+(Get-Content "$out\$Prefix-$Name.err" -Raw))
    } finally {
        if ($proc) {
            if (!$proc.HasExited) {$proc.Kill();$proc.WaitForExit()}
            $proc.Dispose()
        }
    }
}
$devices=Invoke-RebootFastboot 'devices' @('devices')
if ($devices -notmatch '(?im)^62bc28a1\s+fastboot\s*$') {throw 'No independent fastboot enumeration'}
$devices
Invoke-RebootFastboot 'reboot' @('-s','62bc28a1','reboot')
[ordered]@{utc=[DateTime]::UtcNow.ToString('o');serial='62bc28a1';no_flash=$true;reboot_success=$true;processes_disposed=$true} | ConvertTo-Json | Set-Content "$out\$Prefix-reboot.json"
