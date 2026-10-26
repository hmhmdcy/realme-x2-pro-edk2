$ErrorActionPreference='Stop'
$rxDest=Join-Path $PSScriptRoot 'guard-tests.json'
if(Test-Path -LiteralPath $rxDest){throw 'Output exists.'}
. (Join-Path $PSScriptRoot 'eud-driver-trial.ps1')
$rxActual=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'compatibility-audit.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$rxBase=[ordered]@{target=$rxActual.target;is_64bit=$true;is_admin=$true;present_9505_count=1;all_eud_nodes_ok=$true;other_eud_nodes_ok=$true;known_owner_count=0;usb_attached=$false;package_hashes_valid=$true;secureboot=0;test_signing_allowed=$true;test_certificate_trusted=$true;original_bound=$true;candidate_bound=$false;candidate_certificate_current=$true}
$rxCases=@(
  @{name='selected_test_environment_install_guard';action='Install';changes=@{};allow=$true},
  @{name='wrong_control_pid';action='Install';changes=@{target='USB\VID_05C6&PID_9501\dummy'};allow=$false},
  @{name='multiple_present_9505';action='Install';changes=@{present_9505_count=2};allow=$false},
  @{name='active_serial_owner';action='Install';changes=@{known_owner_count=1};allow=$false},
  @{name='usb_relay_attached';action='Install';changes=@{usb_attached=$true};allow=$false},
  @{name='altered_package';action='Install';changes=@{package_hashes_valid=$false};allow=$false},
  @{name='untrusted_test_certificate';action='Install';changes=@{test_certificate_trusted=$false};allow=$false},
  @{name='expired_test_certificate';action='Install';changes=@{candidate_certificate_current=$false};allow=$false},
  @{name='test_signing_off';action='Install';changes=@{test_signing_allowed=$false};allow=$false},
  @{name='secureboot_on';action='Install';changes=@{secureboot=1};allow=$false},
  @{name='non_elevated_install';action='Install';changes=@{is_admin=$false};allow=$false},
  @{name='unknown_existing_driver';action='Install';changes=@{original_bound=$false};allow=$false},
  @{name='candidate_failed_load_restore_allowed';action='Restore';changes=@{original_bound=$false;candidate_bound=$true;all_eud_nodes_ok=$false;test_signing_allowed=$false;secureboot=1;test_certificate_trusted=$false};allow=$true},
  @{name='broken_control_blocks_restore';action='Restore';changes=@{original_bound=$false;candidate_bound=$true;all_eud_nodes_ok=$false;other_eud_nodes_ok=$false};allow=$false},
  @{name='unrelated_driver_restore_refused';action='Restore';changes=@{candidate_bound=$false};allow=$false}
)
$rxResults=@()
foreach($rxCase in $rxCases){
  $rxFixture=[ordered]@{};foreach($rxKey in $rxBase.Keys){$rxFixture[$rxKey]=$rxBase[$rxKey]};foreach($rxKey in $rxCase.changes.Keys){$rxFixture[$rxKey]=$rxCase.changes[$rxKey]}
  $rxReasons=@(Get-Rx63Refusals ([pscustomobject]$rxFixture) $rxCase.action)
  $rxAllow=($rxReasons.Count -eq 0)
  if($rxAllow -ne $rxCase.allow){throw ('Guard case failed: '+$rxCase.name)}
  $rxResults += [ordered]@{case=$rxCase.name;action=$rxCase.action;guard_allows=$rxAllow;expected_allows=$rxCase.allow}
}
$rxReal=$rxActual.state;$rxReal | Add-Member -NotePropertyName other_eud_nodes_ok -NotePropertyValue $true
$rxRealReasons=@(Get-Rx63Refusals $rxReal 'Install')
if($rxRealReasons.Count -ne 3){throw 'Actual host install refusal differs.'}
$rxBinding=Get-Rx63Binding $rxActual.target
if($rxBinding.port -ne 'COM14' -or $rxBinding.inf -ne 'oem102.inf'){throw 'Corrected live port/binding read differs.'}
if([Rx63.DeviceDriver]::StageCalls -ne 0 -or [Rx63.DeviceDriver]::InstallCalls -ne 0){throw 'Guard tests invoked mutation.'}
$rxReport=[ordered]@{utc=[DateTime]::UtcNow.ToString('o');cases=$rxResults;actual_host_refusals=$rxRealReasons;corrected_live_binding=$rxBinding;stage_calls=[Rx63.DeviceDriver]::StageCalls;install_calls=[Rx63.DeviceDriver]::InstallCalls;limits='Pure gate fixtures plus live read-only binding; no staging, installation, signature/security change, serial open or USB data.'}
[IO.File]::WriteAllText($rxDest,($rxReport | ConvertTo-Json -Depth 8).Replace("`r`n","`n")+"`n",[Text.UTF8Encoding]::new($false))
Write-Output ('15 guard cases pass; actual host blocked; COM14 read from device hardware parameters; zero mutation calls.')
