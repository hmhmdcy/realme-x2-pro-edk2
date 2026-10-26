$ErrorActionPreference='Stop'
$rxTarget='USB\VID_05C6&PID_9505\8&5580DC5&0&5'
$rxKey='Registry::HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Class\{4d36e978-e325-11ce-bfc1-08002be10318}\0008'
$rxInstalled=Get-ItemProperty -LiteralPath $rxKey
$rxSig=Get-AuthenticodeSignature -LiteralPath 'C:\Windows\System32\drivers\qcusbser.sys'
$rxBoot=Get-ItemProperty -LiteralPath 'Registry::HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\SecureBoot\State'
$rxDeviceGuard=Get-CimInstance -Namespace root\Microsoft\Windows\DeviceGuard -ClassName Win32_DeviceGuard
$rxHardware=Get-PnpDeviceProperty -InstanceId $rxTarget -KeyName DEVPKEY_Device_HardwareIds
$rxInf='C:\Windows\INF\oem102.inf'
$rxState=[ordered]@{
  utc=[DateTime]::UtcNow.ToString('o'); target=$rxTarget;
  driver=($rxInstalled | Select-Object DriverDesc,ProviderName,DriverVersion,InfPath,InfSection,MatchingDeviceId);
  hardware_ids=$rxHardware.Data;
  installed_inf_sha256=(Get-FileHash -LiteralPath $rxInf).Hash.ToLower();
  signature_status=$rxSig.Status.ToString(); signer_subject=$rxSig.SignerCertificate.Subject;
  secureboot_registry_enabled=$rxBoot.UEFISecureBootEnabled;
  device_guard=($rxDeviceGuard | Select-Object VirtualizationBasedSecurityStatus,SecurityServicesConfigured,SecurityServicesRunning);
  changes='Read-only; no driver install, registry writes, boot/security settings or phone I/O'
}
if($rxInstalled.InfPath -ne 'oem102.inf' -or $rxInstalled.DriverVersion -ne '2.1.3.5' -or $rxSig.Status -ne 'Valid'){throw 'Installed driver differs from expected baseline.'}
$rxDest='E:\edk2-samurai-out\rx61\host-binding.json'
if(Test-Path -LiteralPath $rxDest){throw 'Binding snapshot exists.'}
[IO.File]::WriteAllText($rxDest,($rxState | ConvertTo-Json -Depth 6).Replace("`r`n","`n")+"`n",[Text.UTF8Encoding]::new($false))
$rxState | ConvertTo-Json -Depth 6
