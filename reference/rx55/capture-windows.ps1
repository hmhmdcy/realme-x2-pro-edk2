$ErrorActionPreference='Stop'
$root='E:\edk2-samurai-out\rx55'
$hashes=[ordered]@{
    'EudRxAudit.cs'='006731216176277609d2cff890fe06d8ee9ea99488bea3584036b9b84c673dd7'
    'EudSerialPerf.cs'='249b3d470ee8172fd2bb07376aa15707b82cb732ad78ddd1ef300ddc7e4ae5d6'
    'eud-terminal-rx-perf.ps1'='418979e3c6d4321cc39d23eba8d7cc73b31aa8be5e0a5a3d47c76937fa3d1817'
}
foreach ($item in $hashes.GetEnumerator()) {
    if ((Get-FileHash -LiteralPath (Join-Path $root $item.Key)).Hash.ToLower() -ne $item.Value) { throw "Frozen diagnostic mismatch: $($item.Key)" }
}
$devices=@(Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -like 'USB\VID_05C6&PID_950*' } | Select-Object Status,FriendlyName,InstanceId)
$owners=@(Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'eud-terminal.*\.ps1|eud-console-overlap\.ps1|eud-usb-.*\.py|eud-step.*\.ps1' -and $_.ProcessId -ne $PID } | Select-Object ProcessId,Name,CommandLine)
$usbipd=(& 'C:\Program Files\usbipd-win\usbipd.exe' list | Out-String)
if ($LASTEXITCODE -ne 0) { throw 'usbipd list failed' }
$target=@($usbipd -split "`r?`n" | Where-Object { $_ -match '05c6:950[15]' })
if ($devices.Count -ne 3 -or @($devices | Where-Object Status -ne 'OK').Count -or $owners.Count -or $target.Count -ne 2 -or ($target -join "`n") -match 'Attached') { throw 'Single-owner device preflight failed' }
if ((Get-FileHash -LiteralPath 'E:\eud-host\eud-terminal.ps1').Hash.ToLower() -ne '9c7a16f1f389a0dbbf3436f1383221cdf6c00e348f25b6e3590a479dab103d57') { throw 'Installed terminal differs' }
$state=[ordered]@{utc=(Get-Date).ToUniversalTime().ToString('o'); devices=$devices; owners=$owners; target_usbipd=$target; frozen=$hashes; single_owner=$true; no_reset=$true; no_flash=$true; no_admin_etw=$true}
[IO.File]::WriteAllText((Join-Path $root 'before-state.json'),($state | ConvertTo-Json -Depth 6).Replace("`r`n","`n")+"`n",[Text.UTF8Encoding]::new($false))
& (Join-Path $root 'eud-terminal-rx-perf.ps1') -Port COM14 -Native -RxAudit -AuditMaxSeconds 180 -LogBase (Join-Path $root 'windows-perf-01')
