"""Authenticate one stored batch, validate explicit framing, then check normal policy."""
from pathlib import Path
import importlib.util,json,os,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
capture=load('profile_review_capture',HERE/'capture.py');u=capture.u
def read(path):return json.loads(path.read_bytes())
def main():
 out=u.OUT;raw=out/'capture-raw';request=read(out/'capture-request.json');request_raw=(out/'capture-request.json').read_bytes();reply=read(out/'capture-fetch/reply.json')
 assert reply['current_boot']==request['identity']['boot_id']
 assert reply['worker']['status'] in ['absent','zombie'] and reply['supervisor']['status'] in ['absent','zombie']
 assert (raw/'request-private.json').read_bytes()==(raw/'device-stage/request-private.json').read_bytes()==request_raw
 assert (raw/'stage-worker.py').read_bytes()==(out/'capture-worker-template.py').read_bytes()==capture.worker_source()
 assert (raw/'worker.py').read_bytes()==(out/'capture-wrapper.py').read_bytes() and (raw/'supervisor.py').read_bytes()==(u.POST/'pm-smoke-supervisor.py').read_bytes()
 intent=read(raw/'launch-private.json');assert intent['worker_sha256']==u.sha((raw/'worker.py').read_bytes()) and intent['boot_id']==request['identity']['boot_id']
 terminal=read(raw/'worker-terminal-private.json');process=read(raw/'worker-process-private.json');device=read(raw/'device-stage/process-private.json');worker=read(raw/'device-stage/result.json')
 assert terminal['terminal'] and terminal['returncode']==0 and terminal['receipt_error'] is None and terminal['process']==process
 assert process['pid']==device['pid'] and process['startticks']==device['start_ticks'] and process['argv']==device['argv']
 assert process==reply['worker']['receipt']
 assert read(raw/'supervisor-process-private.json')==read(raw/'supervisor-launch-private.json')==reply['supervisor']['receipt']
 assert device['worker_sha256']==request['worker_sha256']==u.sha((raw/'stage-worker.py').read_bytes())
 assert worker['request_sha256']==u.sha(request_raw) and worker['terminal'] and worker['identity_match'] and worker['identity_before']==worker['identity_after'] and not worker['errors']
 identity=worker['identity_before'];assert all(identity[k]==v for k,v in request['identity'].items())
 c=read(HERE/'cohort-r2-result.json');assert identity['manifest_sha256']==c['target_manifest_sha256'] and identity['protection_ko_sha256']==c['target_protection_sha256'] and identity['loaded_note_sha256']==c['target_protection_note_sha256']
 assert identity['guard_sha256']==request['adoption']['guard_sha256'] and device['boot_id']==request['identity']['boot_id']
 tests=read(capture.PROFILE/'test-result.json');decoder=Path(tests['private_output'])/'frame-decoder-profile';parser=load('profile_review_frozen_parser',capture.PROFILE/'parse-saved-profile.py')
 assert u.sha((capture.PROFILE/'parse-saved-profile.py').read_bytes())==tests['source_files']['parse-saved-profile.py']
 before=(raw/'device-stage/cache-before-private.txt').read_bytes();after=(raw/'device-stage/cache-after-private.txt').read_bytes()
 assert worker['raw_before_sha256']==u.sha(before) and worker['raw_after_sha256']==u.sha(after)
 first=parser.parse_saved_profile(before,decoder,tests['decoder_sha256'],profile='observed-2719-0056-3')
 parsed=parser.parse_saved_profile(after,decoder,tests['decoder_sha256'],profile='observed-2719-0056-3');header=parsed['header']
 assert first['header']['attempted']==0 and worker['capture_write_attempted'] and header['attempted']==header['terminal']==1
 if worker['write_error'] is None:assert worker['write_return']==8 and header['error']==0
 else:
  code=worker['write_error']['errno'];assert type(code) is int and 0<code<=4095 and code!=114 and worker['write_return'] is None and header['error']==-code
 assert worker['started_ns']<=worker['write_started_ns']<=header['started_ns']<=header['ended_ns']<=worker['write_ended_ns']<=worker['cache_after_read_ns']<=worker['ended_ns']
 u.save(out/'capture-analysis.json',parsed)
 post=load('profile_review_postboot',HERE/'postboot.py');post_request=read(out/'postboot-request.json');source=post.collector()
 code=('REQUEST='+repr(post_request)+'\nEXPECTED_CACHE='+repr(u.sha(after))+'\n').encode()+source+br'''
validate_request(REQUEST);check_identity(identity(),REQUEST['guard'])
assert Path('/sys/module/samurai_gauge_protection/parameters/observed_2719_diagnostic').read_text().strip()=='Y'
assert sha(Path('/sys/module/samurai_gauge_protection/notes/.note.gnu.build-id').read_bytes())==NEW_COHORT['target_protection_note_sha256']
assert sha(Path('/usr/share/samurai-charging/manifest.json').read_bytes())==NEW_COHORT['target_manifest_sha256']
assert sha(Path('/usr/sbin/samurai-charging').read_bytes())==NEW_COHORT['target_service_sha256']
ps=Path('/sys/class/power_supply');client=Path('/sys/bus/i2c/devices/0-005c')
raw=dict(telemetry_before=read(client/'telemetry'),source={n:read(ps/'samurai-usb-input'/n) for n in ['online','usb_type','current_max','input_current_limit']},
 charger={n:read(ps/'mp2650-input'/n) for n in ['status','health','online','charge_behaviour','input_current_limit','constant_charge_current','constant_charge_voltage']},
 protection_state=read('/sys/devices/platform/samurai-gauge-protection/protection_state'),telemetry_after=read(client/'telemetry'),
 config_max_power_ma=read('/sys/kernel/config/usb_gadget/samurai/configs/c.1/MaxPower'))
checked=check_charging(raw);assert checked['ready'] and checked['native_ua']==checked['input_ua']==500000
cache=Path('/sys/devices/platform/samurai-gauge-protection/mac_evidence').read_bytes();assert sha(cache)==EXPECTED_CACHE
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0' and not Path('/sys/class/rtc/rtc0/wakealarm').read_text().strip()
print(json.dumps(dict(charging=checked,raw=raw,cache_sha256=sha(cache),boot_id=REQUEST['new_boot_id'],taint=0,dmesg=command(['dmesg']))))
'''
 close=u.call('capture-closeout',code);assert close['boot_id']==request['identity']['boot_id'] and close['cache_sha256']==u.sha(after)
 baseline=read(out/('postboot-r2' if (out/'postboot-r2').exists() else 'postboot')/'reply.json')['raw']['dmesg']['stdout'];log=close['dmesg']['stdout'];assert log.startswith(baseline),'kernel log wrapped; do not claim a fault delta'
 delta={name:log[len(baseline):].count(name) for name in ['WARNING:','Oops:','refcount_t: underflow','gpu fault:','NGD resume failed','fatal error received','Unhandled context fault:','Kernel panic - not syncing']};assert not any(delta.values())
 stage_raws=list(out.glob('raw-*/device-stage/result.json'));assert len(stage_raws)==1;stage=read(stage_raws[0]);stage_term=read(stage_raws[0].parent.parent/'worker-terminal-private.json')
 assert stage['staged'] and stage['disk_state']=='all_new_fsynced' and stage_term['terminal'] and stage_term['returncode']==0 and not stage['primary_error'] and not stage['recovery_error']
 assert read(out/'postboot-reviewed.json')['passed'] and read(out/'adopt/reply.json')['twelve_passed']
 result=dict(passed=bool(parsed['sequence_complete']),installed=True,source_authenticated=True,batch_time_bound=True,sequence_complete=parsed['sequence_complete'],
  explicit_profile='observed-2719-0056-3',fresh_DeviceType2719_validated=True,source_boot_id=request['identity']['boot_id'],
  target_protection_sha256=c['target_protection_sha256'],target_manifest_sha256=c['target_manifest_sha256'],target_service_sha256=c['target_service_sha256'],retained_USB_PM_fix_sha256=c['retained_usb_sha256'],
  before_after_BatteryStatus_real=bool(header['battery_before_valid'] and header['battery_after_valid']),BatteryStatus_mask_stable=parsed['battery_status_mask_stable'],
  batch_duration_ns=parsed['batch_duration_ns'],frames={f'{frame["cmd"]:04x}':frame.get('decoded') for frame in parsed['frames']},
  compatibility_verified=False,TCA_classification='UNVERIFIED',charge_or_recharge_authorized=False,whole_device_PM_accepted=False,
  one_capture_store=True,runtime_retry_permitted=False,charging_post_capture=close['charging'],fault_delta=delta,taint=0,carrier_writes=0,
  old_failed_schema1_size4_batch_preserved=True,r2_partial_stage_restored_before_independent_r3=True,
  evidence=dict(private_directory=str(out),cache_sha256=u.sha(after),worker_sha256=request['worker_sha256'],store_result_sha256=u.sha((raw/'device-stage/result.json').read_bytes())))
 u.save(u.ROOT/'reference/charging-management-20261023/protection-profile-live001-result.json',result)
 pointer=u.BASE/'boot-adoption-private.json';previous=(out/'adoption-pointer.json').read_bytes();assert pointer.read_bytes()==previous
 current=json.loads(previous);current.update(protection_diagnostic_capture_completed=bool(parsed['sequence_complete']),protection_capture_source_authenticated=True,
  protection_capture_cache_sha256=u.sha(after),protection_capture_result_sha256=u.sha((u.ROOT/'reference/charging-management-20261023/protection-profile-live001-result.json').read_bytes()),TCA_classification_verified=False)
 u.save(out/'adoption-pointer-after-capture.json',current);temp=u.BASE/'profile-protection-capture-next-private.json';u.create(temp,(json.dumps(current,indent=2)+'\n').encode());assert pointer.read_bytes()==previous;temp.replace(pointer)
 fd=os.open(pointer.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)
 return {k:result[k] for k in ['passed','sequence_complete','batch_duration_ns','BatteryStatus_mask_stable','TCA_classification','charging_post_capture']}
if __name__=='__main__':print(json.dumps(main(),indent=2))
