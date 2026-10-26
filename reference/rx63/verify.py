"""Verify frozen RX63 evidence; no native API, staging, serial or device writes."""
from pathlib import Path
import hashlib
import json

root = Path(__file__).resolve().parent
entries=[line.split('  ',1) for line in (root/'SHA256SUMS').read_text().splitlines()]
assert len(entries)==len({name for _,name in entries})
for digest,name in entries:
    assert Path(name).name==name
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest, name
read=lambda name: json.loads((root/name).read_text(encoding='utf-8-sig'))
audit=read('compatibility-audit-final.json')
assert audit['action']=='Audit' and audit['status']=='completed' and not audit['executed']
assert audit['stage_calls']==audit['install_calls']==0 and audit['package_hashes_unchanged_after']
assert audit['binding_before']==audit['binding_after'] and audit['binding_after']['port']=='COM14'
assert audit['binding_after']['inf']=='oem102.inf'
assert audit['structure_sizes']==[32,584,1568,1584]
assert audit['candidate_node']['Section']=='EudInstall' and audit['candidate_node']['Version']=='5.47.2.26'
assert audit['rollback_node']['Section']=='QportInstall00' and audit['rollback_node']['Version']=='2.1.3.5'
for name in ['candidate_node','rollback_node']:
    assert audit[name]['HardwareIds'].lower()=='usb\\vid_05c6&pid_9505'
state=audit['state']
assert state['original_bound'] and not state['candidate_bound']
assert state['code_integrity_options_hex']=='0x0000F401'
assert not state['test_signing_allowed'] and state['hvci_kernel_enforced']
assert state['secureboot']==1 and not state['test_certificate_trusted']
assert len(audit['install_refusals'])==3
tests=read('guard-tests.json')
assert len(tests['cases'])==15 and all(x['guard_allows']==x['expected_allows'] for x in tests['cases'])
assert tests['stage_calls']==tests['install_calls']==0
assert next(x for x in tests['cases'] if x['case']=='candidate_failed_load_restore_allowed')['guard_allows']
assert tests['corrected_live_binding']['port']=='COM14'
zlp=read('zlp-source-audit.json')
assert zlp['load_callback']=='QCPNP_EvtDeviceAdd' and zlp['not_reread_by_ordinary_FileCreate']
assert zlp['default'] and not zlp['value_semantics']['dword_zero']
assert zlp['historical_endpoint_max_packet']==16 and not zlp['fresh_endpoint_query_performed']
assert zlp['based_on_requested_length_not_successful_completion']
assert not zlp['source_changed'] and not zlp['registry_changed'] and not zlp['hardware_validated']
post=read('post-state.json'); baseline=read('baseline-state.json')
assert len(post['nodes'])==3 and all(x['Status']=='OK' for x in post['nodes'])
assert not post['known_owners'] and not post['active_eud_trace'] and not post['ewdk_iso_attached']
assert post['temporary_values_absent'] and post['hashes']==baseline['hashes']
assert post['installed_inf']=='oem102.inf' and post['installed_version']=='2.1.3.5'
native=(root/'EudDeviceDriver.cs').read_text()
assert 'SetupCopyOEMInfW' in native and 'DiInstallDevice(' in native
assert 'UpdateDriverForPlugAndPlayDevices(' not in native and 'DiInstallDriver(' not in native
assert 'parameters.Flags |= 0x00010000' in native and 'parameters.FlagsEx |= 0x00000800' in native
assert 'finally' in native and 'SetupDiDestroyDriverInfoList(set' in native and 'Marshal.FreeHGlobal(memory)' in native
script=(root/'eud-driver-trial.ps1').read_text()
assert "[string]$Action='Audit'" in script and 'StageAndBind($InstanceId' in script
assert 'Start-Process' not in script and 'bcdedit' not in script and 'Import-Certificate' not in script
assert 'NeedReboot' in script and 'no automatic reboot' in script
assert "'\\Device Parameters'" in script and 'PLUGPLAY_REGKEY_DRIVER' in (root/'zlp-source-audit.json').read_text()
assert {p.name for p in root.iterdir() if p.is_file()}=={name for _,name in entries}|{'SHA256SUMS'}
print(json.dumps({'frozen_files_verified':len(entries),'native_metadata_compatibility_verified':True,'guard_cases_verified':15,'actual_stage_calls':0,'actual_install_calls':0,'hardware_validated':False,'goal_complete':False}))
