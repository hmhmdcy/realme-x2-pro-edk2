$ErrorActionPreference='Stop'
$out='E:\RealmeX2Pro edk2\reference\kernel74'
$pnp=@(Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -match 'VID_0525|VID_05C6&PID_950' } | Select-Object Status,FriendlyName,InstanceId)
if ($pnp.Count -ne 5 -or @($pnp | Where-Object {$_.Status -ne 'OK'}).Count -ne 0) {throw 'Expected five healthy EUD/NCM nodes'}
$usbipd=& 'C:\Program Files\usbipd-win\usbipd.exe' list 2>&1 | Out-String
if ($LASTEXITCODE -ne 0) {throw 'USBIPD state unavailable'}
if ($usbipd -notmatch '6-5\s+05c6:9505.*Shared' -or $usbipd -match '6-5\s+05c6:9505.*Attached') {throw 'EUD is not released to Windows Shared'}
$owners=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'eudtool|comtool|comrecv|comlog|eud-terminal|ssh.exe|scp.exe' } | Select-Object Name,ProcessId,CommandLine)
if ($owners.Count -ne 0) {throw 'A task host connection remains active'}
$pnp | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath "$out/host-pnp.json" -Encoding utf8
$usbipd | Set-Content -LiteralPath "$out/host-usbipd.txt" -Encoding utf8
[ordered]@{utc=[DateTime]::UtcNow.ToString('o');pnp_nodes=$pnp.Count;pnp_ok=$true;eud_windows_shared=$true;eud_attached=$false;owners=$owners} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath "$out/host-final.json" -Encoding utf8
Get-Content -LiteralPath "$out/host-final.json"
