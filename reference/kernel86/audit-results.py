"""Audit native failure, source corrections and the first real display snapshot."""
from pathlib import Path
import hashlib,json,re,subprocess
O=Path('/mnt/e/edk2-samurai-out/kernel86');W=Path('/mnt/e/RealmeX2Pro edk2');K=Path('/home/cy122/x2pro-linux/linux')
sha=lambda d:hashlib.sha256(d).hexdigest()
header=O.parent/'kernel85/cyborg-oplus_mp2650.h'
manifest=json.loads((O.parent/'kernel85/cyborg-mp-header-manifest.json').read_text())
assert sha(header.read_bytes())==manifest['sha256']
h=header.read_text()
assert re.search(r'REG13_MP2650_VIN_POWER_GOOD_YES\s+0\s',h)
assert re.search(r'REG13_MP2650_VIN_POWER_GOOD_NO\s+BIT\(1\)',h)
source=(W/'reference/kernel86/mp2650_charger.c').read_text()
assert 'i2c_smbus_read_byte_data' in source and 'attempt < 3' in source
assert 'return -ENODATA;' in source and 'set_property' not in source
assert not re.search(r'i2c_smbus_write|regmap_write|i2c_master_send|i2c_smbus_read_word|i2c_smbus_read_block',source)
assert (K/'drivers/power/supply/mp2650_charger.c').read_text()==source
subprocess.run(['git','-C',str(K),'apply','--reverse','--check',str(W/'reference/kernel86/mainline-mp2650-input-status.patch')],check=True)
first=json.loads((O/'candidate-validation.json').read_text());final=json.loads((O/'candidate-final-validation.json').read_text())
assert sha((W/'reference/kernel86/mp2650_charger-first.c').read_bytes())==first['driver_sha256']
assert sha(source.encode())==final['driver_sha256']
assert not final['deployment_done'] and not final['persistent_DT_binding']
probe=(O/'native-property-probe.txt').read_text()
assert probe.count('property=online\n1\nexit=0')==5
assert probe.count('property=status\nFull\nexit=0')==5
assert all((O/('native-'+n+'.txt')).stat().st_size==0 for n in ['sample1','sample2','final-input'])
values={}
for prop in ['voltage_now','current_now']:
    values[prop]={'valid_values':[int(v) for v in re.findall('property='+prop+r'\n(\d+)\nexit=0',probe)],
        'read_failures':len(re.findall('property='+prop+r'\ncat: read error: Resource temporarily unavailable\nexit=1',probe))}
    assert values[prop]['valid_values'] and values[prop]['read_failures']
core=(K/'drivers/power/supply/power_supply_sysfs.c').read_text()
assert 'ret == -ENODEV || ret == -ENODATA || ret == -EINVAL' in core
def regs(name):
    return {int(r,16):int(v,16) for r,v in re.findall(r'reg=0x([0-9a-f]+) value=0x([0-9a-f]+)',(O/name).read_text())}
baseline=regs('input-after-registers.txt');statuses={}
for name in ['native-before-registers.txt','native-after-registers.txt','prefinal-registers.txt','fault-registers.txt']:
    values_now=regs(name);assert len(values_now)==12
    assert {r:v for r,v in values_now.items() if r!=0x13}=={r:v for r,v in baseline.items() if r!=0x13}
    statuses[name]=values_now[0x13]
snapshot=(O/'prefinal-snapshot.txt').read_bytes();trace=(O/'prefinal-trace.txt').read_text()
assert snapshot==(O/'fault-snapshot.txt').read_bytes()
assert trace==(O/'fault-trace.txt').read_text()
assert 'snapshot:count=0' in (O/'prefinal-trace-settings.txt').read_text()
assert (O/'fault-trace-settings.txt').read_text().splitlines()[3]=='0'
assert '378.497165: dpu_enc_frame_done_timeout: id=35, event=2' in trace
text=snapshot.decode()
for fragment in ['378.330844: dpu_enc_kickoff: id=35','378.420888: dpu_enc_frame_done_cb: id=35, idx=0, frame_busy_mask=1',
                 '378.484053: dpu_enc_rc: begin: id:35, sw_event:5','378.484082: dpu_enc_rc: end: id:35, sw_event:5']:
    assert fragment in text
stats=(O/'fault-trace-stats.txt').read_text()
dropped=[int(x) for x in re.findall(r'^dropped events: (\d+)$',stats,re.M)]
commit_overruns=[int(x) for x in re.findall(r'^commit overrun: (\d+)$',stats,re.M)]
assert len(dropped)==len(commit_overruns)==8 and not any(dropped+commit_overruns)
physical=(K/'drivers/gpu/drm/msm/disp/dpu1/dpu_encoder_phys_cmd.c').read_text()
assert 'new_cnt = atomic_add_unless(&phys_enc->pending_kickoff_cnt, -1, 0);' in physical
events=[json.loads(s) for s in (O/'final-f1-wsl.events.jsonl').read_text().splitlines()]
assert not any(e['event'] in ['out_submit','out_complete','receipt'] for e in events)
assert (O/'final-f1-wsl.raw').stat().st_size==0
assert not (O/'final-flash-validation.json').exists()
result={'audit':'PASS','meaning':'Evidence integrity and observed limitations, not hardware acceptance',
 'source':{'OEM_header':manifest,'MPS_datasheet_url':'https://www.monolithicpower.com/en/documentview/productdocument/index/version/2/document_type/Datasheet/lang/en/sku/MP2650GV/',
    'MPS_REG13_ACOK_active_high':True,'MPS_CHG_STAT_code3':'charge termination','OEM_constants_reversed':True,
    'OEM_macro_runtime_impact_verified':False,'PDF_download_completed':False,'PDF_visual_verified':False},
 'native_first':{'online_status_successful_property_reads':5,'status_successful_property_reads':5,'observed_status':'Full',
    'ADC_properties':values,'empty_uevent_captures':3,'complete_interface_verified':False,'configuration_data_writes':0,
    'raw_address_busy_refusal':True,'current_driver_bound':False,'persistent_DT_binding':False,
    'eleven_configuration_values_unchanged':True,'status_register_samples':statuses},
 'candidate_final':{'build_version':87,'built_without_warnings':True,'ADC_attempt_limit':3,'unavailable_ADC_errno':'ENODATA',
    'uevent_error_semantics_checked_against_local_core':True,'hardware_tested':False,'flashed':False},
 'display':{'first_triggered_snapshot_sha256':sha(snapshot),'first_triggered_snapshot_bytes':len(snapshot),
    'main_trace_timeout_timestamp':378.497165,'last_kickoff_timestamp':378.330844,'last_done_callback_timestamp':378.420888,
    'last_idle_IRQ_disable_timestamp':378.484053,'kickoff_to_done_ms':round((378.420888-378.330844)*1000,3),
    'done_to_timeout_ms':round((378.497165-378.420888)*1000,3),'idle_to_timeout_ms':round((378.497165-378.484053)*1000,3),
    'final_timeout_count':2,'final_underruns':0,'trace_on':0,'snapshot_remaining_count':0,
    'snapshot_not_overwritten_after_capture':True,'main_trace_dropped_events_per_CPU':dropped,'main_trace_commit_overruns_per_CPU':commit_overruns,
    'pp_tx_done_new_count_field_is_boolean_return_not_pending_count':True,'root_cause_fixed':False,'optical_recurrence_verified':False},
 'aborted_deployment':{'PowerShell_native_exit_did_not_automatically_stop_sequence':True,'sequence_manually_interrupted':True,
    'F1_OUT_submission_recorded':False,'F1_receipt_recorded':False,'device_still_same_boot':True,'usbipd_detached_after_interruption':True},
 'complete_hardware_goal':'active','charge_control_or_protection_accepted':False}
(O/'results-audit.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
