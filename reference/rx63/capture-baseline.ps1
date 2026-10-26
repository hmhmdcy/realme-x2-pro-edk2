$ErrorActionPreference='Stop'
$rxDest='E:\edk2-samurai-out\rx63\baseline-state.json'
if(Test-Path -LiteralPath $rxDest){throw 'Snapshot exists; preserve historical evidence.'}
$rxTarget='USB\VID_05C6&PID_9505\8&5580DC5&0&5'
$rxDriverKey=(Get-PnpDeviceProperty -InstanceId $rxTarget -KeyName DEVPKEY_Device_Driver).Data
$rxProperties=Get-ItemProperty -LiteralPath ('Registry::HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Class\'+$rxDriverKey)
$rxNodes=@(Get-PnpDevice -PresentOnly | Where-Object {$_.InstanceId -match '^USB\\VID_05C6&PID_950[015]'} | Select-Object Status,Class,FriendlyName,InstanceId)
$rxOwners=@(Get-CimInstance Win32_Process | Where-Object {$_.ProcessId -ne $PID -and $_.CommandLine -match 'eud-terminal.*\.ps1|eud-console-overlap\.ps1|eud-usb-.*\.py|eud-step.*\.ps1|capture-windows-(?:first-status|parity|even)\.ps1|driver-log-etw-admin\.ps1'} | Select-Object ProcessId,Name)
$rxUsb=(& 'C:\Program Files\usbipd-win\usbipd.exe' list | Out-String)
if($LASTEXITCODE -ne 0){throw 'USBIP ownership read failed.'}
$rxHashes=[ordered]@{}
foreach($rxFile in @('C:\Windows\System32\drivers\qcusbser.sys','E:\eud-host\eud-terminal.ps1','E:\edk2-samurai-out\logdump-rx53-console-rx.img')){$rxHashes[$rxFile]=(Get-FileHash -LiteralPath $rxFile).Hash.ToLower()}
$rxGuard=Get-CimInstance -Namespace root\Microsoft\Windows\DeviceGuard -ClassName Win32_DeviceGuard
$rxSig=Get-AuthenticodeSignature -LiteralPath 'C:\Windows\System32\drivers\qcusbser.sys'
$rxIso=Get-DiskImage -ImagePath 'E:\edk2-samurai-out\rx61\EWDK_ge_release_svc_prod1_26100_250904-1728.iso'
$rxOs=Get-CimInstance Win32_OperatingSystem
$rxState=[ordered]@{
  utc=[DateTime]::UtcNow.ToString('o');observation='RX62 fresh read-only state RX63 baseline before read-only SetupAPI compatibility audit; no phone I/O'
  nodes=$rxNodes;known_owners=$rxOwners;temporary_values_absent=(!$rxProperties.PSObject.Properties['QCDriverConfig'] -and !$rxProperties.PSObject.Properties['QCDriverLoggingDirectory'])
  usbipd=$rxUsb;hashes=$rxHashes;active_eud_trace=((& logman.exe query -ets | Out-String) -match 'EUD-RX(?:58|59|60|61|62|63)')
  target=$rxTarget;driver_key=$rxDriverKey;installed_inf=$rxProperties.InfPath;installed_version=$rxProperties.DriverVersion;installed_signature=$rxSig.Status.ToString()
  secureboot_registry_enabled=(Get-ItemProperty -LiteralPath 'Registry::HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\SecureBoot\State').UEFISecureBootEnabled
  device_guard=[ordered]@{VirtualizationBasedSecurityStatus=$rxGuard.VirtualizationBasedSecurityStatus;SecurityServicesRunning=@($rxGuard.SecurityServicesRunning)}
  os=[ordered]@{caption=$rxOs.Caption;version=$rxOs.Version;build=$rxOs.BuildNumber;architecture=$rxOs.OSArchitecture}
  ewdk_iso_attached=$rxIso.Attached
  driver_installed=$false;hardware_validated=$false;changes='Read-only; no serial open, driver/registry/security changes, flashing or reboot'
}
if($rxNodes.Count -ne 3 -or @($rxNodes | Where-Object Status -ne 'OK').Count -or $rxOwners.Count -or !$rxState.temporary_values_absent -or $rxState.active_eud_trace -or $rxUsb -notmatch '(?m)^6-5\s+05c6:9505\s+.*Shared\s*$' -or $rxUsb -match '(?m)^6-5\s+.*Attached' -or $rxIso.Attached){throw 'Restored baseline differs.'}
if($rxProperties.InfPath -ne 'oem102.inf' -or $rxProperties.DriverVersion -ne '2.1.3.5' -or $rxSig.Status -ne 'Valid'){throw 'Installed original driver differs.'}
[IO.File]::WriteAllText($rxDest,($rxState | ConvertTo-Json -Depth 7).Replace("`r`n","`n")+"`n",[Text.UTF8Encoding]::new($false))
$rxState | ConvertTo-Json -Depth 7
