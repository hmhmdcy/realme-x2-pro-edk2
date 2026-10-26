$ErrorActionPreference='Stop'
$k71root='E:\edk2-samurai-out\kernel71'
$k71before=Get-Content -LiteralPath 'E:\edk2-samurai-out\kernel66\baseline-state.json' -Raw | ConvertFrom-Json
$k71nodes=@(Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -match '^USB\\VID_05C6&PID_950[015]' } | Select-Object Status,Class,FriendlyName,InstanceId)
if ($k71nodes.Count -ne 3 -or @($k71nodes | Where-Object Status -ne 'OK').Count) { throw 'Expected three healthy EUD nodes' }
$k71target=@($k71nodes | Where-Object InstanceId -match 'PID_9505')[0].InstanceId
$k71key=(Get-PnpDeviceProperty -InstanceId $k71target -KeyName DEVPKEY_Device_Driver).Data
$k71props=Get-ItemProperty -LiteralPath ('Registry::HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Class\'+$k71key)
$k71owners=@(Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -ne $PID -and $_.CommandLine -match 'eud-terminal.*\.ps1|eud-console-overlap\.ps1|eud-usb-.*\.py|eud-step.*\.ps1|eudtool\.exe|fastboot\.exe' } | Select-Object ProcessId,Name)
$k71linuxOwners=(& 'C:\Windows\System32\wsl.exe' -d Ubuntu -- bash -c "ps -eo pid,ppid,args | grep -E '[p]ython3 .*/eud-usb|[e]ud-terminal|[e]udtool' || true" | Out-String).Trim()
$k71usb=(& 'C:\Program Files\usbipd-win\usbipd.exe' list | Out-String)
if ($LASTEXITCODE -ne 0 -or $k71usb -notmatch '(?m)^6-5\s+05c6:9505\s+[^\r\n]*Shared\s*$' -or $k71owners.Count -or $k71linuxOwners) { throw 'Expected released, unattached USB target' }
$k71hashes=[ordered]@{}
foreach ($k71prop in $k71before.hashes.PSObject.Properties) {
    $k71hashes[$k71prop.Name]=(Get-FileHash -LiteralPath $k71prop.Name).Hash.ToLowerInvariant()
    if ($k71hashes[$k71prop.Name] -ne $k71prop.Value) { throw "Original file changed: $($k71prop.Name)" }
}
$k71loggingAbsent=(!$k71props.PSObject.Properties['QCDriverConfig'] -and !$k71props.PSObject.Properties['QCDriverLoggingDirectory'])
$k71traces=(& 'C:\Windows\System32\logman.exe' query -ets | Out-String)
$k71traceActive=$k71traces -match 'EUD-RX[0-9]+'
if (!$k71loggingAbsent -or $k71traceActive -or $k71props.InfPath -ne 'oem102.inf' -or $k71props.DriverVersion -ne '2.1.3.5') { throw 'Unexpected original driver/logging state' }
$k71facts=Get-Content -LiteralPath "$k71root\finish-facts.validated.txt" -Raw
if ($k71facts -notmatch '(?m)^a31c1158-fbca-4515-83ac-1a3b40ee808e\n0\n') { throw 'Incomplete fresh Linux facts' }
$k71state=[ordered]@{utc=[DateTime]::UtcNow.ToString('o');phase='finish-state';nodes=$k71nodes;known_owners=$k71owners;known_linux_owners=$k71linuxOwners;usbipd=$k71usb;hashes=$k71hashes;driver_inf=$k71props.InfPath;driver_version=$k71props.DriverVersion;temporary_logging_absent=$k71loggingAbsent;active_eud_trace=$k71traceActive;flashed_partitions=@('boot','logdump');boot_written=$true;logdump_written=$true;userdata_written=$false;gpt_written=$false;last_confirmed_mode='Linux';last_confirmed_kernel='#61';last_confirmed_boot_id='a31c1158-fbca-4515-83ac-1a3b40ee808e';gadget_binding_attempted=$false;eud_control_changes=$false;retained_logdump_image_sha256=(Get-FileHash -LiteralPath 'E:\edk2-samurai-out\logdump-k67-usb.img').Hash.ToLowerInvariant()}
[IO.File]::WriteAllText("$k71root\finish-state.json",($k71state | ConvertTo-Json -Depth 6).Replace("`r`n","`n")+"`n",[Text.UTF8Encoding]::new($false))
Write-Output 'Saved finish-state: COM14 Windows/Shared/unattached; three nodes OK; no known owners; original files unchanged; one boot/logdump deployment; no gadget/control change.'
