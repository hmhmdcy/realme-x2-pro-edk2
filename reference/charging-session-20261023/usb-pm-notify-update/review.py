"""Independent raw audit and adoption of the completed module-only PM increment."""
from pathlib import Path
import importlib.util,json,os,re,sys
sys.dont_write_bytecode=True
spec=importlib.util.spec_from_file_location('notify_review_update',Path(__file__).resolve().parent/'host.py')
u=importlib.util.module_from_spec(spec);spec.loader.exec_module(u)
def read(p):return json.loads(p.read_bytes())
def main():
 out=u.OUT;raw=out/'pm-raw';request=read(out/'postboot-request.json');boot=request['new_boot_id']
 scope={};exec(compile((out/'postboot-collector.py').read_bytes(),'<retained-actual-collector>','exec'),scope)
 stage_rows=list(out.glob('raw-*/device-stage/result.json'));assert len(stage_rows)==1
 stage_root=stage_rows[0].parent.parent;stage=read(stage_rows[0]);term=read(stage_root/'worker-terminal-private.json')
 assert stage['staged'] and stage['terminal'] and stage['disk_state']=='all_new_fsynced' and stage['stop_verified'] and not stage['primary_error'] and not stage['recovery_error']
 assert term['terminal'] and term['returncode']==0 and term['receipt_error'] is None and term['process']==read(stage_root/'worker-process-private.json')
 assert (stage_root/'stage-worker.py').read_bytes()==(out/'stage-worker.py').read_bytes()
 assert (stage_root/'supervisor.py').read_bytes()==(u.POST/'pm-smoke-supervisor.py').read_bytes()
 assert read(stage_root/'device-stage/before-private.json')['mac_evidence']==read(stage_root/'device-stage/after-private.json')['mac_evidence']
 assert (raw/'worker.py').read_bytes()==(out/'pm-worker.py').read_bytes()
 assert (raw/'supervisor.py').read_bytes()==(u.POST/'pm-smoke-supervisor.py').read_bytes()
 terminal=read(raw/'worker-terminal-private.json');assert terminal['terminal'] and terminal['returncode']==0 and terminal['receipt_error'] is None
 assert terminal['process']==read(raw/'worker-process-private.json')
 for name in ['before-private.json','after-private.json']:
  actual=read(raw/name);assert scope['audit'](actual['raw'],request)==actual['result'];assert actual['result']['passed'] and len(actual['result']['checks'])==12 and not actual['result']['errors']
 result=read(raw/'result-private.json');assert result['device_functional_passed'] and result['terminal'] and result['transaction']['mem_write_attempts']==1
 assert result['suspend_stats_delta']['success']==1 and result['suspend_stats_delta']['fail']==0 and not any(result['fault_delta'].values())
 cleanup=read(raw/'trace-cleanup-private.json');trace_raw=(raw/'pm-wakeup-trace-private.txt').read_bytes();trace=trace_raw.decode()
 assert cleanup['evidence']['sha256']==u.sha(trace_raw) and not cleanup['cleanup_errors'] and not cleanup['global_trace_modified'] and not cleanup['wakeup_policy_modified']
 assert len(cleanup['evidence']['per_cpu'])==8
 for stats in cleanup['evidence']['per_cpu'].values():
  for name in ['overrun','commit overrun','dropped events']:assert re.search(r'^'+name+r': 0$',stats,re.M)
 suspend=trace.split('suspend_resume: dpm_prepare[2] begin',1)[1].split('suspend_resume: machine_suspend[1] end',1)[0]
 assert 'wakeup_source_activate: samurai-usb-input' not in suspend
 assert 'samurai_usb_complete' in trace.split('suspend_resume: dpm_complete[16] begin',1)[1]
 assert read(out/'fastboot-reboot-terminal.json')==dict(terminal=True,returncode=0)
 fresh=u.call('closeout',('EXPECTED='+repr(boot)+'\n').encode()+br'''
from pathlib import Path
import hashlib,json
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==EXPECTED
guard=Path('/var/lib/samurai/irq-native-usb-pm-activate-notify-20261024-01-adopted/boot-id-private.txt')
assert guard.read_bytes()==(EXPECTED+'\n').encode()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert Path('/sys/class/power_supply/samurai-gauge-protection/health').read_text().strip()=='Good'
assert Path('/sys/class/power_supply/samurai-usb-input/input_current_limit').read_text().strip()=='500000'
assert hashlib.sha256(Path('/sys/module/samurai_usb_input/notes/.note.gnu.build-id').read_bytes()).hexdigest()=='f3c8d708a7122549a8733b5c171a2c2895e63eccaa76e31e5dfdbd9ca2ff46ae'
assert not Path('/sys/class/rtc/rtc0/wakealarm').read_text().strip()
assert not Path('/sys/kernel/tracing/instances/pm504-notify-live-20261024-01').exists()
print(json.dumps(dict(boot_id=EXPECTED,guard_path=str(guard),USB500_restored=True,health='Good',taint=0,alarm_empty=True,owned_trace_removed=True)))
''')
 pointer=u.BASE/'boot-adoption-private.json';before=(out/'previous-pointer.json').read_bytes();assert pointer.read_bytes()==before
 current=json.loads(before);current.update(guard_path=fresh['guard_path'],boot_id=boot,charging_manifest_sha256=stage['new_manifest_sha256'],
  postboot_raw_sha256=u.sha((out/'postboot-r2/stdout-private.json').read_bytes()),fresh_validation_sha256=u.sha((raw/'fresh-adoption-private.json').read_bytes()),
  stage_transaction_id=u.TX,profile='forward_504_pm_notify_r2',PM_suspend_resume_verified=True,PM_single_RTC_residency_seconds=result['transaction']['estimated_residency_seconds'],
  USB_original_key_recovery_verified=True,USB_physical_wakeup_verified=False,whole_device_PM_verified=False)
 u.save(out/'adoption-pointer.json',current);temp=u.BASE/'notify-r2-adoption-next-private.json';u.create(temp,(json.dumps(current,indent=2)+'\n').encode());assert pointer.read_bytes()==before;temp.replace(pointer)
 fd=os.open(pointer.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)
 public=dict(passed=True,installed=True,boot_id=boot,kernel_version=u.VERSION,module_sha256='ebfcb45d436f0f08dcaf4e400ea18b18cf3bd208863de33444e76c20faab4624',
  manifest_sha256=stage['new_manifest_sha256'],carrier_writes=0,source_d046_guard_and_cache_preserved=True,stage_original_child_terminal0=True,new_boot_twelve_checks=True,
  PM_before_after_twelve_checks=True,PM_worker_original_child_terminal0=True,PM_result=result,scoped_trace_zero_loss_all8=True,
  no_USB_PSY_wakeup_during_prepare_to_machine_resume=True,deferred_software_notice_observed_in_complete=True,trace_cleanup_verified=True,
  USB_original_key_NCM_restored_without_user_replug=True,current_native_and_physical_input_ua=500000,adopted=True,
  physical_USB_wakeup_accepted=False,whole_device_PM_accepted=False,
  failed_prechecks_preserved=['EUD-on restart inspect refused before any reboot claim; actual EUD-off tail then used once','first postboot read before protection autostart; later independent read passed'],
  remaining=['physical USB IRQ wake from standby','temperature boundary physical stimuli','full low-charge/full/recharge cycle','exact2719/TCA and source route/FLOAT/PD/high-power branches'],
  evidence=dict(private_directory=str(out),hashes={name:u.sha((raw/name).read_bytes()) for name in ['worker.py','before-private.json','after-private.json','result-private.json','worker-terminal-private.json','pm-wakeup-trace-private.txt','trace-cleanup-private.json']}))
 u.save(u.ROOT/'reference/charging-management-20261023/native-pm-notify-r2-result.json',public)
 return dict(passed=True,residency_seconds=result['transaction']['estimated_residency_seconds'],adopted=True,physical_USB_wakeup_accepted=False)
if __name__=='__main__':print(json.dumps(main(),indent=2))
