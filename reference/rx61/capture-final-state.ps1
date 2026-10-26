$ErrorActionPreference='Stop'
$rxKey='Registry::HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Class\{4d36e978-e325-11ce-bfc1-08002be10318}\0008'
$rxProperties=Get-ItemProperty -LiteralPath $rxKey
$rxNodes=@(Get-PnpDevice -PresentOnly | Where-Object {$_.InstanceId -match '^USB\\VID_05C6&PID_950[015]'} | Select-Object Status,Class,FriendlyName,InstanceId)
$rxOwners=@(Get-CimInstance Win32_Process | Where-Object {$_.ProcessId -ne $PID -and $_.CommandLine -match 'eud-terminal.*\.ps1|eud-console-overlap\.ps1|eud-usb-.*\.py|eud-step.*\.ps1|capture-windows-(?:first-status|parity|even)\.ps1|driver-log-etw-admin\.ps1'} | Select-Object ProcessId,Name)
$rxUsb=(& 'C:\Program Files\usbipd-win\usbipd.exe' list | Out-String)
if($LASTEXITCODE -ne 0){throw 'USBIP ownership read failed.'}
$rxHashes=[ordered]@{}
foreach($rxFile in @('C:\Windows\System32\drivers\qcusbser.sys','E:\eud-host\eud-terminal.ps1','E:\edk2-samurai-out\logdump-rx53-console-rx.img')){$rxHashes[$rxFile]=(Get-FileHash -LiteralPath $rxFile).Hash.ToLower()}
$rxState=[ordered]@{utc=[DateTime]::UtcNow.ToString('o');observation='RX61 independent post-preparation baseline; no new device I/O or install';nodes=$rxNodes;known_owners=$rxOwners;temporary_values_absent=(!$rxProperties.PSObject.Properties['QCDriverConfig'] -and !$rxProperties.PSObject.Properties['QCDriverLoggingDirectory']);usbipd=$rxUsb;hashes=$rxHashes;active_eud_trace=((& logman.exe query -ets | Out-String) -match 'EUD-RX(?:58|59|60|61)')}
if($rxNodes.Count -ne 3 -or @($rxNodes | Where-Object Status -ne 'OK').Count -or $rxOwners.Count -or !$rxState.temporary_values_absent -or $rxState.active_eud_trace -or $rxUsb -notmatch '(?m)^6-5\s+05c6:9505\s+.*Shared\s*$' -or $rxUsb -match '(?m)^6-5\s+.*Attached'){throw 'Restored baseline differs.'}
$rxDest='E:\edk2-samurai-out\rx61\post-state.json'
if(Test-Path -LiteralPath $rxDest){throw 'Snapshot already exists.'}
[IO.File]::WriteAllText($rxDest,($rxState | ConvertTo-Json -Depth 6).Replace("`r`n","`n")+"`n",[Text.UTF8Encoding]::new($false))
$rxState | ConvertTo-Json -Depth 6
