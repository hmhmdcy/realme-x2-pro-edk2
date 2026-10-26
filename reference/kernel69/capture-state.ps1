$ErrorActionPreference='Stop'
$k69root='E:\edk2-samurai-out\kernel69'
$k69before=Get-Content -LiteralPath 'E:\edk2-samurai-out\kernel66\baseline-state.json' -Raw | ConvertFrom-Json
$k69nodes=@(Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -match '^USB\\VID_05C6&PID_950[015]' } | Select-Object Status,Class,FriendlyName,InstanceId)
if ($k69nodes.Count -ne 3 -or @($k69nodes | Where-Object Status -ne 'OK').Count) { throw 'Expected three healthy EUD nodes' }
$k69target=@($k69nodes | Where-Object InstanceId -match 'PID_9505')[0].InstanceId
$k69key=(Get-PnpDeviceProperty -InstanceId $k69target -KeyName DEVPKEY_Device_Driver).Data
$k69props=Get-ItemProperty -LiteralPath ('Registry::HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Class\'+$k69key)
$k69owners=@(Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -ne $PID -and $_.CommandLine -match 'eud-terminal.*\.ps1|eud-console-overlap\.ps1|eud-usb-.*\.py|eud-step.*\.ps1|eudtool\.exe|fastboot\.exe' } | Select-Object ProcessId,Name)
$k69linuxOwners=(& 'C:\Windows\System32\wsl.exe' -d Ubuntu -- bash -c "ps -eo pid,ppid,args | grep -E '[p]ython3 .*/eud-usb|[e]ud-terminal|[e]udtool' || true" | Out-String).Trim()
$k69usb=(& 'C:\Program Files\usbipd-win\usbipd.exe' list | Out-String)
if ($LASTEXITCODE -ne 0 -or $k69usb -notmatch '(?m)^6-5\s+05c6:9505\s+[^\r\n]*Shared\s*$' -or $k69owners.Count -or $k69linuxOwners) { throw 'Expected released, unattached USB target' }
$k69hashes=[ordered]@{}
foreach ($k69prop in $k69before.hashes.PSObject.Properties) {
    $k69hashes[$k69prop.Name]=(Get-FileHash -LiteralPath $k69prop.Name).Hash.ToLowerInvariant()
    if ($k69hashes[$k69prop.Name] -ne $k69prop.Value) { throw "Original file changed: $($k69prop.Name)" }
}
$k69loggingAbsent=(!$k69props.PSObject.Properties['QCDriverConfig'] -and !$k69props.PSObject.Properties['QCDriverLoggingDirectory'])
$k69traces=(& 'C:\Windows\System32\logman.exe' query -ets | Out-String)
$k69traceActive=$k69traces -match 'EUD-RX(?:5[7-9]|6[0-9])'
if (!$k69loggingAbsent -or $k69traceActive -or $k69props.InfPath -ne 'oem102.inf' -or $k69props.DriverVersion -ne '2.1.3.5') { throw 'Unexpected original driver/logging state' }
$k69facts=Get-Content -LiteralPath "$k69root\driver-facts.validated.txt" -Raw
if ($k69facts -notmatch '(?m)^afbbf870-b998-43d8-ab3d-42b3c68c0122\n0\n') { throw 'Incomplete fresh Linux facts' }
$k69state=[ordered]@{utc=[DateTime]::UtcNow.ToString('o');phase='finish-state';nodes=$k69nodes;known_owners=$k69owners;known_linux_owners=$k69linuxOwners;usbipd=$k69usb;hashes=$k69hashes;driver_inf=$k69props.InfPath;driver_version=$k69props.DriverVersion;temporary_logging_absent=$k69loggingAbsent;active_eud_trace=$k69traceActive;flashed_partitions=@();boot_written=$false;logdump_written=$false;userdata_written=$false;gpt_written=$false;last_confirmed_mode='Linux';last_confirmed_kernel='#60';last_confirmed_boot_id='afbbf870-b998-43d8-ab3d-42b3c68c0122';gadget_binding_attempted=$false;eud_control_changes=$false;retained_logdump_image_sha256=(Get-FileHash -LiteralPath 'E:\edk2-samurai-out\logdump-k67-usb.img').Hash.ToLowerInvariant()}
[IO.File]::WriteAllText("$k69root\finish-state.json",($k69state | ConvertTo-Json -Depth 6).Replace("`r`n","`n")+"`n",[Text.UTF8Encoding]::new($false))
Write-Output 'Saved finish-state: COM14 Windows/Shared/unattached; three nodes OK; no known owners; original files unchanged; no flash or gadget/control change.'
