$ErrorActionPreference='Stop'
$k68root='E:\edk2-samurai-out\kernel68'
$k68before=Get-Content -LiteralPath 'E:\edk2-samurai-out\kernel66\baseline-state.json' -Raw | ConvertFrom-Json
$k68nodes=@(Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -match '^USB\\VID_05C6&PID_950[015]' } | Select-Object Status,Class,FriendlyName,InstanceId)
if ($k68nodes.Count -ne 3 -or @($k68nodes | Where-Object Status -ne 'OK').Count) { throw 'Expected three healthy EUD nodes' }
$k68target=@($k68nodes | Where-Object InstanceId -match 'PID_9505')[0].InstanceId
$k68key=(Get-PnpDeviceProperty -InstanceId $k68target -KeyName DEVPKEY_Device_Driver).Data
$k68props=Get-ItemProperty -LiteralPath ('Registry::HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Class\'+$k68key)
$k68owners=@(Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -ne $PID -and $_.CommandLine -match 'eud-terminal.*\.ps1|eud-console-overlap\.ps1|eud-usb-.*\.py|eud-step.*\.ps1|eudtool\.exe|fastboot\.exe' } | Select-Object ProcessId,Name)
$k68linuxOwners=(& 'C:\Windows\System32\wsl.exe' -d Ubuntu -- bash -c "ps -eo pid,ppid,args | grep -E '[p]ython3 .*/eud-usb|[e]ud-terminal|[e]udtool' || true" | Out-String).Trim()
$k68usb=(& 'C:\Program Files\usbipd-win\usbipd.exe' list | Out-String)
if ($LASTEXITCODE -ne 0 -or $k68usb -notmatch '(?m)^6-5\s+05c6:9505\s+[^\r\n]*Shared\s*$' -or $k68owners.Count -or $k68linuxOwners) { throw 'Expected released, unattached USB target' }
$k68hashes=[ordered]@{}
foreach ($k68prop in $k68before.hashes.PSObject.Properties) {
    $k68hashes[$k68prop.Name]=(Get-FileHash -LiteralPath $k68prop.Name).Hash.ToLowerInvariant()
    if ($k68hashes[$k68prop.Name] -ne $k68prop.Value) { throw "Original file changed: $($k68prop.Name)" }
}
$k68loggingAbsent=(!$k68props.PSObject.Properties['QCDriverConfig'] -and !$k68props.PSObject.Properties['QCDriverLoggingDirectory'])
$k68traces=(& 'C:\Windows\System32\logman.exe' query -ets | Out-String)
$k68traceActive=$k68traces -match 'EUD-RX(?:5[7-9]|6[0-8])'
if (!$k68loggingAbsent -or $k68traceActive -or $k68props.InfPath -ne 'oem102.inf' -or $k68props.DriverVersion -ne '2.1.3.5') { throw 'Unexpected original driver/logging state' }
$k68facts=Get-Content -LiteralPath "$k68root\opp-facts.validated.txt" -Raw
if ($k68facts -notmatch '(?m)^afbbf870-b998-43d8-ab3d-42b3c68c0122\n0\n' -or $k68facts -notmatch '/opp-2956800000') { throw 'Incomplete fresh Linux facts' }
$k68flash=Get-Content -LiteralPath "$k68root\boot-flash-validation.json" -Raw | ConvertFrom-Json
if (!$k68flash.flash_success -or $k68flash.partition -ne 'boot') { throw 'Missing boot-only flash proof' }
$k68state=[ordered]@{utc=[DateTime]::UtcNow.ToString('o');phase='finish-state';nodes=$k68nodes;known_owners=$k68owners;known_linux_owners=$k68linuxOwners;usbipd=$k68usb;hashes=$k68hashes;driver_inf=$k68props.InfPath;driver_version=$k68props.DriverVersion;temporary_logging_absent=$k68loggingAbsent;active_eud_trace=$k68traceActive;flashed_partitions=@('boot');boot_written=$true;logdump_written=$false;userdata_written=$false;gpt_written=$false;last_confirmed_mode='Linux';last_confirmed_kernel='#60';last_confirmed_boot_id='afbbf870-b998-43d8-ab3d-42b3c68c0122';boot_image_sha256=$k68flash.image_sha256;retained_logdump_image_sha256=(Get-FileHash -LiteralPath 'E:\edk2-samurai-out\logdump-k67-usb.img').Hash.ToLowerInvariant()}
[IO.File]::WriteAllText("$k68root\finish-state.json",($k68state | ConvertTo-Json -Depth 6).Replace("`r`n","`n")+"`n",[Text.UTF8Encoding]::new($false))
Write-Output 'Saved finish-state: COM14 Windows/Shared/unattached; three nodes OK; no known owners; original files unchanged.'
