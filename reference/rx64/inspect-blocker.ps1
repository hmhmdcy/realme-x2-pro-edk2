$ErrorActionPreference='Stop'
$rxDest='E:\edk2-samurai-out\rx64\blocker-snapshot.json'
if(Test-Path -LiteralPath $rxDest){throw 'Preserve existing snapshot; no overwrite.'}
. 'E:\edk2-samurai-out\rx63\eud-driver-trial.ps1'
Assert-Rx63Packages 'E:\edk2-samurai-out\rx62\package-test-signed' 'E:\edk2-samurai-out\rx61\rollback-qcusbser-2.1.3.5'
$rxTarget='USB\VID_05C6&PID_9505\8&5580DC5&0&5'
$rxNodes=@(Get-PnpDevice -PresentOnly | Where-Object {$_.InstanceId -match '^USB\\VID_05C6&PID_950[015]'} | Select-Object Status,Class,FriendlyName,InstanceId)
$rxBinding=Get-Rx63Binding $rxTarget
$rxCi=[Rx63.DeviceDriver]::CurrentCodeIntegrity()
$rxSecure=(Get-ItemProperty -LiteralPath 'Registry::HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\SecureBoot\State').UEFISecureBootEnabled
$rxOwners=@(Get-CimInstance Win32_Process | Where-Object {$_.ProcessId -ne $PID -and $_.CommandLine -match 'eud-terminal.*\.ps1|eud-console-overlap\.ps1|eud-usb-.*\.py|eud-step.*\.ps1|capture-windows-(?:first-status|parity|even)\.ps1|driver-log-etw-admin\.ps1'} | Select-Object ProcessId,Name)
$rxJobs=@(Get-CimInstance Win32_Process | Where-Object {$_.ProcessId -ne $PID -and $_.CommandLine -match '(?:rx61|rx62).*(?:download-ewdk|assemble-ewdk|build-candidate|sign-candidate|offline-signing)|(?:curl|7z).*EWDK_ge_release'} | Select-Object ProcessId,Name)
$rxUsb=(& 'C:\Program Files\usbipd-win\usbipd.exe' list | Out-String)
if($LASTEXITCODE -ne 0){throw 'USBIP read failed.'}
$rxUsbLine=@($rxUsb -split "`r?`n" | Where-Object {$_ -match '^\S+\s+05c6:9505\s+'})
if($rxUsbLine.Count -ne 1){throw 'Target USBIP line unavailable/ambiguous.'}
$rxProps=Get-ItemProperty -LiteralPath ('Registry::HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Class\'+$rxBinding.driver_key)
$rxCertTrust=[ordered]@{}
foreach($rxStoreName in @('Root','TrustedPublisher')){
  $rxStore=[Security.Cryptography.X509Certificates.X509Store]::new($rxStoreName,[Security.Cryptography.X509Certificates.StoreLocation]::LocalMachine)
  try {$rxStore.Open([Security.Cryptography.X509Certificates.OpenFlags]::ReadOnly);$rxCertTrust[$rxStoreName]=@($rxStore.Certificates | Where-Object Thumbprint -eq '58A7050746D4222DFAB3C81EAA4DF9BDCE53CD48').Count} finally {$rxStore.Close();$rxStore.Dispose()}
}
$rxHashes=[ordered]@{}
foreach($rxFile in @('C:\Windows\System32\drivers\qcusbser.sys','E:\eud-host\eud-terminal.ps1','E:\edk2-samurai-out\logdump-rx53-console-rx.img')){$rxHashes[$rxFile]=(Get-FileHash -LiteralPath $rxFile).Hash.ToLower()}
$rxIso=Get-DiskImage -ImagePath 'E:\edk2-samurai-out\rx61\EWDK_ge_release_svc_prod1_26100_250904-1728.iso'
$rxTrace=((& logman.exe query -ets | Out-String) -match 'EUD-RX(?:58|59|60|61|62|63|64)')
$rxState=[ordered]@{
  utc=[DateTime]::UtcNow.ToString('o');observation='RX64 blocked audit; native CI query and device/host reads only'
  previous_turn='PROGRESS: RX63 actual compatibility/policy audit, guarded tools and independently verified fork publication'
  nodes=$rxNodes;binding=$rxBinding;known_owners=$rxOwners;known_build_download_sign_jobs=$rxJobs
  code_integrity_options_hex=('0x{0:X8}' -f $rxCi);test_signing_allowed=(($rxCi -band 2) -ne 0);hvci_kernel_enforced=(($rxCi -band 0x400) -ne 0)
  secureboot_registry_enabled=$rxSecure;test_certificate_machine_store_matches=$rxCertTrust
  usbipd_target=$rxUsbLine[0];hashes=$rxHashes;active_eud_trace=$rxTrace;ewdk_iso_attached=$rxIso.Attached
  temporary_logging_absent=(!$rxProps.PSObject.Properties['QCDriverConfig'] -and !$rxProps.PSObject.Properties['QCDriverLoggingDirectory'])
  stage_calls=[Rx63.DeviceDriver]::StageCalls;install_calls=[Rx63.DeviceDriver]::InstallCalls
  candidate_and_rollback_hashes_verified=$true
  hardware_validated=$false;serial_opened=$false;host_policy_changed=$false;phone_flashing_or_reboot=$false
}
if($rxNodes.Count -ne 3 -or @($rxNodes | Where-Object Status -ne 'OK').Count -or $rxOwners.Count -or $rxJobs.Count -or $rxTrace -or $rxIso.Attached -or !$rxState.temporary_logging_absent){throw 'Observed state differs; inspect before blocked classification.'}
if($rxBinding.inf -ne 'oem102.inf' -or $rxBinding.version -ne '2.1.3.5' -or $rxBinding.port -ne 'COM14' -or $rxBinding.binary_sha256 -ne 'ad2ace071d2362d8712820f62570757e1af266a054d2c3d3a6964a41e7cc6151'){throw 'Original binding changed.'}
if($rxCi -ne 0xF401 -or $rxSecure -ne 1 -or $rxState.test_signing_allowed -or $rxUsbLine[0] -notmatch 'Shared\s*$'){throw 'Loading/ownership state changed; reconsider next action.'}
[IO.File]::WriteAllText($rxDest,($rxState | ConvertTo-Json -Depth 7).Replace("`r`n","`n")+"`n",[Text.UTF8Encoding]::new($false))
$rxState | ConvertTo-Json -Depth 7
