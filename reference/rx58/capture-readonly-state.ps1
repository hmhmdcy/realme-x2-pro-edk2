$ErrorActionPreference='Stop'
$rxRoot='E:\edk2-samurai-out\rx58'
$rxKey='Registry::HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Class\{4d36e978-e325-11ce-bfc1-08002be10318}\0008'
$rxProperties=Get-ItemProperty -LiteralPath $rxKey
$rxNodes=@(Get-PnpDevice -PresentOnly | Where-Object {$_.InstanceId -match '^USB\\VID_05C6&PID_950[015]'} | Select-Object Status,Class,FriendlyName,InstanceId)
$rxOwners=@(Get-CimInstance Win32_Process | Where-Object {$_.ProcessId -ne $PID -and $_.CommandLine -match 'eud-terminal.*\.ps1|eud-console-overlap\.ps1|eud-usb-.*\.py|eud-step.*\.ps1|rx(?:57|58)[\\/]capture-windows(?:-02|-first-status)?\.ps1'} | Select-Object ProcessId,Name)
$rxUsb=(& 'C:\Program Files\usbipd-win\usbipd.exe' list | Out-String)
if($LASTEXITCODE -ne 0){throw 'USBIP ownership read failed.'}
$rxHashes=[ordered]@{}
foreach($rxFile in @('C:\Windows\System32\drivers\qcusbser.sys','E:\eud-host\eud-terminal.ps1','E:\edk2-samurai-out\logdump-rx53-console-rx.img')){$rxHashes[$rxFile]=(Get-FileHash -LiteralPath $rxFile).Hash.ToLower()}
$rxState=[ordered]@{utc=[DateTime]::UtcNow.ToString('o');observation='Read-only; no COM open, registry/PnP mutation, UAC, attach, build, flash or phone reboot in RX58 so far.';nodes=$rxNodes;known_owners=$rxOwners;temporary_values_absent=(!$rxProperties.PSObject.Properties['QCDriverConfig'] -and !$rxProperties.PSObject.Properties['QCDriverLoggingDirectory']);usbipd=$rxUsb;hashes=$rxHashes;new_control_exists=(Test-Path -LiteralPath (Join-Path $rxRoot 'control-first-status-01'));new_log_directory_exists=(Test-Path -LiteralPath (Join-Path $rxRoot 'driver-logs-first-status-01'));new_etl_exists=(Test-Path -LiteralPath (Join-Path $rxRoot 'first-status-01.etl'))}
if($rxNodes.Count -ne 3 -or @($rxNodes | Where-Object Status -ne 'OK').Count -or $rxOwners.Count -or !$rxState.temporary_values_absent -or $rxUsb -notmatch '(?m)^6-5\s+05c6:9505\s+.*Shared\s*$' -or $rxUsb -match '(?m)^6-5\s+.*Attached'){throw 'Read-only baseline differs.'}
[IO.File]::WriteAllText((Join-Path $rxRoot 'readonly-state.json'),($rxState | ConvertTo-Json -Depth 6).Replace("`r`n","`n")+"`n",[Text.UTF8Encoding]::new($false))
$rxState | ConvertTo-Json -Depth 6
