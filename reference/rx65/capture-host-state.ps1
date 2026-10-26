param([ValidateSet('baseline','post')][string]$Phase='baseline')
$ErrorActionPreference='Stop'
$rxPath='E:\edk2-samurai-out\rx65\'+$Phase+'-state.json'
if(Test-Path -LiteralPath $rxPath){throw 'Preserve existing state snapshot.'}
$rxNodes=@(Get-PnpDevice -PresentOnly | Where-Object {$_.InstanceId -match '^USB\\VID_05C6&PID_950[015]'} | Select-Object Status,Class,FriendlyName,InstanceId)
$rxTargets=@($rxNodes | Where-Object InstanceId -match '^USB\\VID_05C6&PID_9505\\')
if($rxNodes.Count -ne 3 -or @($rxNodes | Where-Object Status -ne 'OK').Count -or $rxTargets.Count -ne 1){throw 'Require three healthy EUD nodes and one target.'}
$rxTarget=$rxTargets[0].InstanceId
$rxKey=(Get-PnpDeviceProperty -InstanceId $rxTarget -KeyName DEVPKEY_Device_Driver).Data
$rxProps=Get-ItemProperty -LiteralPath ('Registry::HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Class\'+$rxKey)
$rxOwners=@(Get-CimInstance Win32_Process | Where-Object {$_.ProcessId -ne $PID -and $_.CommandLine -match 'eud-terminal.*\.ps1|eud-console-overlap\.ps1|eud-usb-.*\.py|eud-step.*\.ps1|capture-windows-(?:first-status|parity|even)\.ps1|driver-log-etw-admin\.ps1'} | Select-Object ProcessId,Name)
$rxUsb=(& 'C:\Program Files\usbipd-win\usbipd.exe' list | Out-String)
if($LASTEXITCODE -ne 0){throw 'USBIP status query failed.'}
$rxLine=@($rxUsb -split "`r?`n" | Where-Object {$_ -match '^\S+\s+05c6:9505\s+'})
if($rxLine.Count -ne 1 -or $rxLine[0] -notmatch 'Shared\s*$' -or $rxOwners.Count){throw 'Shared/unattached target without owners required.'}
$rxHashes=[ordered]@{}
foreach($rxFile in @('C:\Windows\System32\drivers\qcusbser.sys','E:\eud-host\eud-terminal.ps1','E:\edk2-samurai-out\logdump-rx53-console-rx.img','E:\eud-host\eudtool.exe','E:\eud-host\eudtool.cpp')){$rxHashes[$rxFile]=(Get-FileHash -LiteralPath $rxFile).Hash.ToLower()}
if($rxProps.InfPath -ne 'oem102.inf' -or $rxProps.DriverVersion -ne '2.1.3.5' -or $rxHashes['C:\Windows\System32\drivers\qcusbser.sys'] -ne 'ad2ace071d2362d8712820f62570757e1af266a054d2c3d3a6964a41e7cc6151' -or $rxHashes['E:\eud-host\eud-terminal.ps1'] -ne '9c7a16f1f389a0dbbf3436f1383221cdf6c00e348f25b6e3590a479dab103d57' -or $rxHashes['E:\edk2-samurai-out\logdump-rx53-console-rx.img'] -ne '50f951a4093dab3e4b93339a998b06583a01b75cd3c8cb39f67ca70e84fc5a93'){throw 'Original driver/terminal/logdump changed.'}
$rxState=[ordered]@{utc=[DateTime]::UtcNow.ToString('o');phase=$Phase;nodes=$rxNodes;target=$rxTarget;driver_key=$rxKey;installed_inf=$rxProps.InfPath;installed_version=$rxProps.DriverVersion;known_owners=$rxOwners;usbipd_target=$rxLine[0];busid=($rxLine[0] -split '\s+')[0];hashes=$rxHashes;temporary_logging_absent=(!$rxProps.PSObject.Properties['QCDriverConfig'] -and !$rxProps.PSObject.Properties['QCDriverLoggingDirectory']);active_eud_trace=((& logman.exe query -ets | Out-String) -match 'EUD-RX(?:58|59|60|61|62|63|64|65)');phone_flashing=$false;windows_candidate_installed=$false;windows_policy_changed=$false}
if(!$rxState.temporary_logging_absent -or $rxState.active_eud_trace){throw 'Unexpected logging/trace state.'}
[IO.File]::WriteAllText($rxPath,($rxState | ConvertTo-Json -Depth 6).Replace("`r`n","`n")+"`n",[Text.UTF8Encoding]::new($false))
$rxState | ConvertTo-Json -Depth 6
