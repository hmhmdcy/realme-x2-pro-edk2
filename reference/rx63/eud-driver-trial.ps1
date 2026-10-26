param(
  [ValidateSet('Audit','Install','Restore')][string]$Action='Audit',
  [string]$InstanceId='USB\VID_05C6&PID_9505\8&5580DC5&0&5',
  [string]$Candidate='E:\edk2-samurai-out\rx62\package-test-signed',
  [string]$Rollback='E:\edk2-samurai-out\rx61\rollback-qcusbser-2.1.3.5',
  [string]$OutputPath='E:\edk2-samurai-out\rx63\compatibility-audit.json'
)
$ErrorActionPreference='Stop'
if(!('Rx63.DeviceDriver' -as [type])){Add-Type -Path (Join-Path $PSScriptRoot 'EudDeviceDriver.cs')}

function Get-Rx63Refusals($State,[string]$RequestedAction) {
  $rxReasons=[Collections.Generic.List[string]]::new()
  if(!$State.is_64bit){$rxReasons.Add('A native 64-bit process is required.')}
  if($State.target -notmatch '^USB\\VID_05C6&PID_9505\\'){$rxReasons.Add('Target must be the exact single EUD COM instance.')}
  if($State.present_9505_count -ne 1 -or !$State.other_eud_nodes_ok){$rxReasons.Add('Exactly one present 9505 and normal Control/hub nodes are required.')}
  if($RequestedAction -ne 'Restore' -and !$State.all_eud_nodes_ok){$rxReasons.Add('A normal 9505 node is required before audit/installation.')}
  if($State.known_owner_count -ne 0 -or $State.usb_attached){$rxReasons.Add('A serial/USB owner is active.')}
  if(!$State.package_hashes_valid){$rxReasons.Add('Candidate/rollback bytes differ.')}
  if($RequestedAction -eq 'Install'){
    if(!$State.is_admin){$rxReasons.Add('Installation requires an elevated process in the selected test environment.')}
    if(!$State.test_signing_allowed -or $State.secureboot -ne 0){$rxReasons.Add('Current kernel policy does not allow this self-test-signed candidate.')}
    if(!$State.test_certificate_trusted){$rxReasons.Add('The exact public test certificate is not trusted for this package on this environment.')}
    if(!$State.original_bound){$rxReasons.Add('Initial installation requires the exact original driver bound to this device.')}
    if(!$State.candidate_certificate_current){$rxReasons.Add('The one-use test certificate has expired or is not yet valid.')}
  } elseif($RequestedAction -eq 'Restore'){
    if(!$State.is_admin){$rxReasons.Add('Restore requires an elevated process.')}
    if(!$State.candidate_bound){$rxReasons.Add('Restore is limited to a device bound to this exact candidate.')}
  }
  return $rxReasons.ToArray()
}

function Get-Rx63Binding([string]$Target) {
  $rxKey=(Get-PnpDeviceProperty -InstanceId $Target -KeyName DEVPKEY_Device_Driver).Data
  $rxProps=Get-ItemProperty -LiteralPath ('Registry::HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Class\'+$rxKey)
  $rxService=(Get-PnpDeviceProperty -InstanceId $Target -KeyName DEVPKEY_Device_Service).Data
  $rxImage=(Get-ItemProperty -LiteralPath ('Registry::HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\'+$rxService)).ImagePath
  $rxImage=[Environment]::ExpandEnvironmentVariables($rxImage.Trim('"'))
  if($rxImage.StartsWith('\SystemRoot\',[StringComparison]::OrdinalIgnoreCase)){$rxImage=Join-Path $env:SystemRoot $rxImage.Substring(12)}
  if($rxImage.StartsWith('\??\')){$rxImage=$rxImage.Substring(4)}
  if(!(Test-Path -LiteralPath $rxImage -PathType Leaf)){throw 'Bound service binary path is not a readable file.'}
  $rxInf=Join-Path (Join-Path $env:SystemRoot 'INF') $rxProps.InfPath
  $rxPort=(Get-ItemProperty -LiteralPath ('Registry::HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Enum\'+$Target+'\Device Parameters') -Name PortName -ErrorAction SilentlyContinue).PortName
  [ordered]@{driver_key=$rxKey;inf=$rxProps.InfPath;inf_sha256=(Get-FileHash -LiteralPath $rxInf).Hash.ToLower();version=$rxProps.DriverVersion;service=$rxService;binary=$rxImage;binary_sha256=(Get-FileHash -LiteralPath $rxImage).Hash.ToLower();port=$rxPort}
}

function Assert-Rx63Packages([string]$TestPackage,[string]$OldPackage) {
  $rxExpected=[ordered]@{
    'qcwdfserial.sys'='245e88c2c5818440e04345490159869243a542e997ffa1997aba5460309c777c'
    'qceudexp.inf'='f0217c8ec587fccc0f24e701a3a1cf405f2e25961cd11e56a19682ec923b1495'
    'qceudexp.cat'='9df033f24f3effac2fc29bb5a440d1c54b29c6472ade1165fa6121518d63354f'
    'eud-rx62-test.cer'='bae8c1af8d8ed810ba02ddc8159bc08e20c05e09259be2cc3d9f3dcdbe7ac844'
    'QUALCOMM-LICENSE.txt'='44c38c8e8170268d5c1469c359f46b0a4e11a53f7d68b5a561030c9044b1bb0d'
  }
  foreach($rxName in $rxExpected.Keys){if((Get-FileHash -LiteralPath (Join-Path $TestPackage $rxName)).Hash.ToLower() -ne $rxExpected[$rxName]){throw ('Candidate differs: '+$rxName)}}
  $rxExpected=[ordered]@{
    'qcser.cat'='3f09f7d6d0b24150742eb74895896d75ff57676fbcf3a336a25dc380728496eb'
    'qcser.inf'='dd933233672930b6a138c762f729d92ad984cd1e44abcb16e4ac3878b4305f92'
    'qcser.PNF'='b016ea7656e2c3da04cedb291c16bf384b1acdd5824c8bf958bbc6b94621df38'
    'serial\amd64\qcusbser.sys'='ad2ace071d2362d8712820f62570757e1af266a054d2c3d3a6964a41e7cc6151'
  }
  foreach($rxName in $rxExpected.Keys){if((Get-FileHash -LiteralPath (Join-Path $OldPackage $rxName)).Hash.ToLower() -ne $rxExpected[$rxName]){throw ('Rollback differs: '+$rxName)}}
}

# Dot-source only defines/compiles helpers for guard tests; it performs no audit/install.
if($MyInvocation.InvocationName -eq '.'){return}
if(Test-Path -LiteralPath $OutputPath){throw 'Output already exists; use a fresh path.'}
$rxBefore=$null
$rxResult=$null
$rxReport=[ordered]@{utc=[DateTime]::UtcNow.ToString('o');action=$Action;target=$InstanceId;hardware_validated=$false;executed=$false}
try {
  Assert-Rx63Packages $Candidate $Rollback
  $rxNodes=@(Get-PnpDevice -PresentOnly | Where-Object {$_.InstanceId -match '^USB\\VID_05C6&PID_950[015]'} | Select-Object Status,Class,FriendlyName,InstanceId)
  $rxTargets=@($rxNodes | Where-Object InstanceId -match '^USB\\VID_05C6&PID_9505\\')
  if($rxTargets.Count -ne 1 -or $rxTargets[0].InstanceId -ne $InstanceId){throw 'Exact target is not the sole present EUD COM device.'}
  $rxOwners=@(Get-CimInstance Win32_Process | Where-Object {$_.ProcessId -ne $PID -and $_.CommandLine -match 'eud-terminal.*\.ps1|eud-console-overlap\.ps1|eud-usb-.*\.py|eud-step.*\.ps1|capture-windows-(?:first-status|parity|even)\.ps1|driver-log-etw-admin\.ps1'} | Select-Object ProcessId,Name)
  $rxBefore=Get-Rx63Binding $InstanceId
  $rxCi=[Rx63.DeviceDriver]::CurrentCodeIntegrity()
  $rxSecure=(Get-ItemProperty -LiteralPath 'Registry::HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\SecureBoot\State').UEFISecureBootEnabled
  $rxAdmin=([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
  $rxCert=[Security.Cryptography.X509Certificates.X509Certificate2]::new((Join-Path $Candidate 'eud-rx62-test.cer'))
  try {
    if($rxCert.Thumbprint -ne '58A7050746D4222DFAB3C81EAA4DF9BDCE53CD48'){throw 'Unexpected public certificate.'}
    $rxCertCurrent=($rxCert.NotBefore.ToUniversalTime() -le [DateTime]::UtcNow -and $rxCert.NotAfter.ToUniversalTime() -gt [DateTime]::UtcNow)
    $rxCertTrusted=$true
    foreach($rxStoreName in @('Root','TrustedPublisher')){
      $rxStore=[Security.Cryptography.X509Certificates.X509Store]::new($rxStoreName,[Security.Cryptography.X509Certificates.StoreLocation]::LocalMachine)
      try {$rxStore.Open([Security.Cryptography.X509Certificates.OpenFlags]::ReadOnly);if(@($rxStore.Certificates | Where-Object Thumbprint -eq $rxCert.Thumbprint).Count -ne 1){$rxCertTrusted=$false}}finally{$rxStore.Close();$rxStore.Dispose()}
    }
  } finally {$rxCert.Dispose()}
  $rxUsb='usbipd unavailable on this host'
  if(Test-Path -LiteralPath 'C:\Program Files\usbipd-win\usbipd.exe'){$rxUsb=(& 'C:\Program Files\usbipd-win\usbipd.exe' list | Out-String);if($LASTEXITCODE -ne 0){throw 'USBIP ownership check failed.'}}
  $rxState=[pscustomobject]@{
    target=$InstanceId;is_64bit=[Environment]::Is64BitProcess;is_admin=$rxAdmin;present_9505_count=$rxTargets.Count
    all_eud_nodes_ok=($rxNodes.Count -eq 3 -and @($rxNodes | Where-Object Status -ne 'OK').Count -eq 0)
    other_eud_nodes_ok=(@($rxNodes | Where-Object InstanceId -match '^USB\\VID_05C6&PID_950[01]').Count -eq 2 -and @($rxNodes | Where-Object {$_.InstanceId -match '^USB\\VID_05C6&PID_950[01]' -and $_.Status -ne 'OK'}).Count -eq 0)
    known_owner_count=$rxOwners.Count;usb_attached=($rxUsb -match '(?m)^\S+\s+05c6:9505\s+.*Attached\s*$')
    package_hashes_valid=$true;secureboot=$rxSecure;code_integrity_options_hex=('0x{0:X8}' -f $rxCi)
    test_signing_allowed=(($rxCi -band 2) -ne 0);hvci_kernel_enforced=(($rxCi -band 0x400) -ne 0)
    test_certificate_trusted=$rxCertTrusted;candidate_certificate_current=$rxCertCurrent
    original_bound=($rxBefore.inf_sha256 -eq 'dd933233672930b6a138c762f729d92ad984cd1e44abcb16e4ac3878b4305f92' -and $rxBefore.binary_sha256 -eq 'ad2ace071d2362d8712820f62570757e1af266a054d2c3d3a6964a41e7cc6151')
    candidate_bound=($rxBefore.service -eq 'qceudexp' -and $rxBefore.inf_sha256 -eq 'f0217c8ec587fccc0f24e701a3a1cf405f2e25961cd11e56a19682ec923b1495' -and $rxBefore.binary_sha256 -eq '245e88c2c5818440e04345490159869243a542e997ffa1997aba5460309c777c')
  }
  $rxReport.state=$rxState;$rxReport.binding_before=$rxBefore;$rxReport.nodes_before=$rxNodes
  $rxReport.structure_sizes=[Rx63.DeviceDriver]::StructureSizes()
  $rxReport.refusals=@(Get-Rx63Refusals $rxState $Action)
  if($rxReport.refusals.Count){throw ($rxReport.refusals -join ' ')}
  $rxReport.candidate_node=[Rx63.DeviceDriver]::Audit($InstanceId,(Join-Path $Candidate 'qceudexp.inf'))
  $rxReport.rollback_node=[Rx63.DeviceDriver]::Audit($InstanceId,(Join-Path $Rollback 'qcser.inf'))
  $rxReport.install_refusals=@(Get-Rx63Refusals $rxState 'Install')
  if($Action -ne 'Audit'){
    $rxInf=if($Action -eq 'Install'){Join-Path $Candidate 'qceudexp.inf'}else{Join-Path $Rollback 'qcser.inf'}
    $rxExpected=if($Action -eq 'Install'){'f0217c8ec587fccc0f24e701a3a1cf405f2e25961cd11e56a19682ec923b1495'}else{'dd933233672930b6a138c762f729d92ad984cd1e44abcb16e4ac3878b4305f92'}
    # Revalidate live binding/policy/owner gates immediately before mutation.
    if((Get-Rx63Binding $InstanceId | ConvertTo-Json -Compress) -ne ($rxBefore | ConvertTo-Json -Compress)){throw 'Binding changed during preflight.'}
    if([Rx63.DeviceDriver]::CurrentCodeIntegrity() -ne $rxCi){throw 'Kernel policy changed during preflight.'}
    $rxLiveOwners=@(Get-CimInstance Win32_Process | Where-Object {$_.ProcessId -ne $PID -and $_.CommandLine -match 'eud-terminal.*\.ps1|eud-console-overlap\.ps1|eud-usb-.*\.py|eud-step.*\.ps1|capture-windows-(?:first-status|parity|even)\.ps1|driver-log-etw-admin\.ps1'})
    if($rxLiveOwners.Count){throw 'Owner appeared during preflight.'}
    if(Test-Path -LiteralPath 'C:\Program Files\usbipd-win\usbipd.exe'){$rxLiveUsb=(& 'C:\Program Files\usbipd-win\usbipd.exe' list | Out-String);if($LASTEXITCODE -ne 0 -or $rxLiveUsb -match '(?m)^\S+\s+05c6:9505\s+.*Attached\s*$'){throw 'USBIP ownership changed during preflight.'}}
    Assert-Rx63Packages $Candidate $Rollback
    $rxResult=[Rx63.DeviceDriver]::StageAndBind($InstanceId,$rxInf,$rxExpected)
    $rxReport.executed=$true;$rxReport.native_result=$rxResult
    if($rxResult.NeedReboot){throw 'Windows reports a PC restart is needed. Stop; no automatic reboot or serial test.'}
    $rxAfter=Get-Rx63Binding $InstanceId
    $rxSysExpected=if($Action -eq 'Install'){'245e88c2c5818440e04345490159869243a542e997ffa1997aba5460309c777c'}else{'ad2ace071d2362d8712820f62570757e1af266a054d2c3d3a6964a41e7cc6151'}
    if($rxAfter.inf_sha256 -ne $rxExpected -or $rxAfter.binary_sha256 -ne $rxSysExpected){throw 'Post-bind exact INF/SYS check failed; do not proceed to serial data.'}
    $rxReport.binding_after=$rxAfter
    $rxReport.port_changed=($rxBefore.port -ne $rxAfter.port)
    $rxOtherAfter=@(Get-PnpDevice -PresentOnly | Where-Object {$_.InstanceId -match '^USB\\VID_05C6&PID_950[01]'} | Select-Object Status,Class,FriendlyName,InstanceId)
    $rxOtherBefore=@($rxNodes | Where-Object InstanceId -match '^USB\\VID_05C6&PID_950[01]')
    if(($rxOtherBefore | Sort-Object InstanceId | ConvertTo-Json -Compress) -ne ($rxOtherAfter | Sort-Object InstanceId | ConvertTo-Json -Compress)){throw 'Control/hub state changed; stop before data.'}
  } else {
    $rxAfter=Get-Rx63Binding $InstanceId
    if(($rxAfter | ConvertTo-Json -Compress) -ne ($rxBefore | ConvertTo-Json -Compress)){throw 'Binding changed during read-only audit.'}
    $rxReport.binding_after=$rxAfter
  }
  Assert-Rx63Packages $Candidate $Rollback
  $rxReport.package_hashes_unchanged_after=$true
  $rxReport.status='completed'
} catch {
  $rxReport.status='stopped';$rxReport.error=$_.Exception.Message
  throw
} finally {
  $rxReport.stage_calls=[Rx63.DeviceDriver]::StageCalls;$rxReport.install_calls=[Rx63.DeviceDriver]::InstallCalls
  $rxReport.ended_utc=[DateTime]::UtcNow.ToString('o')
  [IO.File]::WriteAllText($OutputPath,($rxReport | ConvertTo-Json -Depth 9).Replace("`r`n","`n")+"`n",[Text.UTF8Encoding]::new($false))
}
Write-Output ($rxReport | ConvertTo-Json -Depth 9)
