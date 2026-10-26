$ErrorActionPreference='Stop'
$k70root='E:\edk2-samurai-out\kernel70'
$k70before=Get-Content -LiteralPath 'E:\edk2-samurai-out\kernel66\baseline-state.json' -Raw | ConvertFrom-Json
$k70nodes=@(Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -match '^USB\\VID_05C6&PID_950[015]' } | Select-Object Status,Class,FriendlyName,InstanceId)
if ($k70nodes.Count -ne 3 -or @($k70nodes | Where-Object Status -ne 'OK').Count) { throw 'Expected three healthy EUD nodes' }
$k70target=@($k70nodes | Where-Object InstanceId -match 'PID_9505')[0].InstanceId
$k70key=(Get-PnpDeviceProperty -InstanceId $k70target -KeyName DEVPKEY_Device_Driver).Data
$k70props=Get-ItemProperty -LiteralPath ('Registry::HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Class\'+$k70key)
$k70owners=@(Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -ne $PID -and $_.CommandLine -match 'eud-terminal.*\.ps1|eud-console-overlap\.ps1|eud-usb-.*\.py|eud-step.*\.ps1|eudtool\.exe|fastboot\.exe' } | Select-Object ProcessId,Name)
$k70linuxOwners=(& 'C:\Windows\System32\wsl.exe' -d Ubuntu -- bash -c "ps -eo pid,ppid,args | grep -E '[p]ython3 .*/eud-usb|[e]ud-terminal|[e]udtool' || true" | Out-String).Trim()
$k70usb=(& 'C:\Program Files\usbipd-win\usbipd.exe' list | Out-String)
if ($LASTEXITCODE -ne 0 -or $k70usb -notmatch '(?m)^6-5\s+05c6:9505\s+[^\r\n]*Shared\s*$' -or $k70owners.Count -or $k70linuxOwners) { throw 'Expected released, unattached USB target' }
$k70hashes=[ordered]@{}
foreach ($k70prop in $k70before.hashes.PSObject.Properties) {
    $k70hashes[$k70prop.Name]=(Get-FileHash -LiteralPath $k70prop.Name).Hash.ToLowerInvariant()
    if ($k70hashes[$k70prop.Name] -ne $k70prop.Value) { throw "Original file changed: $($k70prop.Name)" }
}
$k70loggingAbsent=(!$k70props.PSObject.Properties['QCDriverConfig'] -and !$k70props.PSObject.Properties['QCDriverLoggingDirectory'])
$k70traces=(& 'C:\Windows\System32\logman.exe' query -ets | Out-String)
$k70traceActive=$k70traces -match 'EUD-RX[0-9]+'
if (!$k70loggingAbsent -or $k70traceActive -or $k70props.InfPath -ne 'oem102.inf' -or $k70props.DriverVersion -ne '2.1.3.5') { throw 'Unexpected original driver/logging state' }
$k70facts=Get-Content -LiteralPath "$k70root\provider-state.validated.txt" -Raw
if ($k70facts -notmatch '(?m)^afbbf870-b998-43d8-ab3d-42b3c68c0122\n0\n') { throw 'Incomplete fresh Linux facts' }
$k70state=[ordered]@{utc=[DateTime]::UtcNow.ToString('o');phase='finish-state';nodes=$k70nodes;known_owners=$k70owners;known_linux_owners=$k70linuxOwners;usbipd=$k70usb;hashes=$k70hashes;driver_inf=$k70props.InfPath;driver_version=$k70props.DriverVersion;temporary_logging_absent=$k70loggingAbsent;active_eud_trace=$k70traceActive;flashed_partitions=@();boot_written=$false;logdump_written=$false;userdata_written=$false;gpt_written=$false;last_confirmed_mode='Linux';last_confirmed_kernel='#60';last_confirmed_boot_id='afbbf870-b998-43d8-ab3d-42b3c68c0122';gadget_binding_attempted=$false;eud_control_changes=$false;retained_logdump_image_sha256=(Get-FileHash -LiteralPath 'E:\edk2-samurai-out\logdump-k67-usb.img').Hash.ToLowerInvariant()}
[IO.File]::WriteAllText("$k70root\finish-state.json",($k70state | ConvertTo-Json -Depth 6).Replace("`r`n","`n")+"`n",[Text.UTF8Encoding]::new($false))
Write-Output 'Saved finish-state: COM14 Windows/Shared/unattached; three nodes OK; no known owners; original files unchanged; no flash or gadget/control change.'
