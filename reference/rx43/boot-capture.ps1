param([Parameter(Mandatory=$true)][string]$Out)
$ErrorActionPreference='Stop'
$taskJob=Start-Job -ScriptBlock { & 'C:\Users\cy122\Downloads\platform-tools\platform-tools\fastboot.exe' -s 62bc28a1 reboot 2>&1; if ($LASTEXITCODE) { throw 'fastboot reboot failed' } }
try {
    if (!(Wait-Job $taskJob -Timeout 12)) { throw 'fastboot reboot timeout' }
    Receive-Job $taskJob -ErrorAction Stop
} finally { if ($taskJob.State -eq 'Running') { Stop-Job $taskJob }; Remove-Job $taskJob }
$deadline=(Get-Date).AddSeconds(45)
$ready=$false
while ((Get-Date) -lt $deadline) {
    $probe=(& 'E:\eud-host\eudtool.exe' probe 2>&1 | Out-String)
    if ($probe -match 'resp \(4\)') { $ready=$true; break }
    Start-Sleep -Milliseconds 300
}
if (!$ready) { throw 'No EUD control response within 45s' }
& 'E:\eud-host\eudtool.exe' com-up
if ($LASTEXITCODE) { throw 'com-up failed' }
$deadline=(Get-Date).AddSeconds(15)
$port=$null
while ((Get-Date) -lt $deadline -and !$port) {
    $devices=@(Get-CimInstance Win32_PnPEntity | Where-Object { $_.Name -match 'EUD.*\(COM\d+\)' -and $_.Status -eq 'OK' })
    if ($devices.Count -eq 1) { $port=[regex]::Match($devices[0].Name,'COM\d+').Value }
    if (!$port) { Start-Sleep -Milliseconds 300 }
}
if (!$port) { throw 'No unique EUD COM owner target' }
& 'E:\RealmeX2Pro edk2\linux-port\uefi-rx-probe\capture.ps1' -Port $port -Seconds 85 -Out $Out
