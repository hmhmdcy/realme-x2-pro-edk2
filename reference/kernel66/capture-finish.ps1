$ErrorActionPreference = 'Stop'
$k66root = 'E:\edk2-samurai-out\kernel66'
$k66before = Get-Content -LiteralPath "$k66root\baseline-state.json" -Raw | ConvertFrom-Json
$k66nodes = @(Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -match '^USB\\VID_05C6&PID_950[015]' } | Select-Object Status,Class,FriendlyName,InstanceId)
if ($k66nodes.Count -ne 3 -or @($k66nodes | Where-Object Status -ne 'OK').Count) { throw 'Expected three healthy EUD nodes' }
$k66target = @($k66nodes | Where-Object InstanceId -match 'PID_9505')[0].InstanceId
$k66key = (Get-PnpDeviceProperty -InstanceId $k66target -KeyName DEVPKEY_Device_Driver).Data
$k66props = Get-ItemProperty -LiteralPath ('Registry::HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Class\'+$k66key)
$k66owners = @(Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -ne $PID -and $_.CommandLine -match 'eud-terminal.*\.ps1|eud-console-overlap\.ps1|eud-usb-.*\.py|eud-step.*\.ps1|eudtool\.exe|fastboot\.exe' } | Select-Object ProcessId,Name)
$k66usb = (& 'C:\Program Files\usbipd-win\usbipd.exe' list | Out-String)
if ($LASTEXITCODE -ne 0 -or $k66usb -notmatch '(?m)^6-5\s+05c6:9505\s+[^\r\n]*Shared\s*$' -or $k66owners.Count) { throw 'Expected released, unattached USB target' }
$k66hashes = [ordered]@{}
foreach ($k66prop in $k66before.hashes.PSObject.Properties) {
    $k66hashes[$k66prop.Name] = (Get-FileHash -LiteralPath $k66prop.Name).Hash.ToLowerInvariant()
    if ($k66hashes[$k66prop.Name] -ne $k66prop.Value) { throw "Original file changed: $($k66prop.Name)" }
}
$k66sourceHashes = [ordered]@{}
foreach ($k66file in @('drivers\tty\serial\eud.c','drivers\tty\serial\eud_earlycon.c','.config','arch\arm64\boot\dts\qcom\sm8150-samurai.dtb')) {
    $k66sourceHashes[$k66file]=(Get-FileHash -LiteralPath ('\\wsl.localhost\Ubuntu\home\cy122\x2pro-linux\linux\'+$k66file)).Hash.ToLowerInvariant()
}
$k66sourceHashes['init']=(Get-FileHash -LiteralPath '\\wsl.localhost\Ubuntu\home\cy122\x2pro-linux\initramfs\init').Hash.ToLowerInvariant()
$k66loggingAbsent = (!$k66props.PSObject.Properties['QCDriverConfig'] -and !$k66props.PSObject.Properties['QCDriverLoggingDirectory'])
$k66traces = (& 'C:\Windows\System32\logman.exe' query -ets | Out-String)
$k66traceActive = $k66traces -match 'EUD-RX(?:5[7-9]|6[0-6])'
if (!$k66loggingAbsent -or $k66traceActive -or $k66props.InfPath -ne 'oem102.inf' -or $k66props.DriverVersion -ne '2.1.3.5') { throw 'Unexpected original driver/logging state' }
$k66state = [ordered]@{utc=[DateTime]::UtcNow.ToString('o');phase='after-three-logdump-flashes-and-map-log-validation';nodes=$k66nodes;known_owners=$k66owners;usbipd=$k66usb;hashes=$k66hashes;source_hashes=$k66sourceHashes;driver_inf=$k66props.InfPath;driver_version=$k66props.DriverVersion;temporary_logging_absent=$k66loggingAbsent;active_eud_trace=$k66traceActive;flashed_partitions=@('logdump','logdump','logdump');boot_written=$false;userdata_written=$false;gpt_written=$false;last_confirmed_mode='Linux';last_confirmed_kernel='#59';last_confirmed_boot_id='87a7b341-6139-4afd-9ca2-3c0b20493e68';live_logdump_sha256='c2658235953cbdb8820cfabe6bee9ab0526b8fceb6b69f71f029174690b16e4d'}
[IO.File]::WriteAllText("$k66root\finish-state.json",($k66state | ConvertTo-Json -Depth 6).Replace("`r`n","`n")+"`n",[Text.UTF8Encoding]::new($false))
$k66state | ConvertTo-Json -Depth 6
