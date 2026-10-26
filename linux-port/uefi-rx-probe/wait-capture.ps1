param([Parameter(Mandatory=$true)][string]$Out, [switch]$StartAbc,
      [ValidateSet('RX38-UEFI','RX39-UEFI','RX41-WAIT')][string]$Marker = 'RX39-UEFI')
$ErrorActionPreference = 'Stop'
$tool = 'E:\eud-host\eudtool.exe'
$deadline = (Get-Date).AddSeconds(60)
$found = $false
while ((Get-Date) -lt $deadline) {
    $probe = (& $tool probe 2>&1 | Out-String)
    if ($probe -match 'resp \(4\)') { $found = $true; break }
    Start-Sleep -Milliseconds 500
}
if (-not $found) { throw 'EUD control did not return in 60 seconds' }
& $tool com-up
$deadline = (Get-Date).AddSeconds(15)
$port = $null
while ((Get-Date) -lt $deadline -and -not $port) {
    foreach ($device in (Get-CimInstance Win32_PnPEntity | Where-Object { $_.Name -match 'EUD.*\(COM\d+\)' -and $_.Status -eq 'OK' })) {
        if ($device.Name -match '\((COM\d+)\)') { $port = $Matches[1]; break }
    }
    if (-not $port) { Start-Sleep -Milliseconds 500 }
}
if (-not $port) { throw 'EUD COM did not enumerate after com-up' }
& "$PSScriptRoot\capture.ps1" -Port $port -Seconds 100 -Out $Out -StartAbc:$StartAbc.IsPresent -Marker $Marker
