"""Audit the actual new-cohort PM evidence and advance only its PM fields."""
from pathlib import Path
import importlib.util,json,os,re,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('profile_pm_review_adapter',HERE/'host.py');a=importlib.util.module_from_spec(s);s.loader.exec_module(a);u=a.u
def read(path):return json.loads(path.read_bytes())
out=u.OUT;raw=out/'pm-raw';request=read(out/'postboot-request.json');source=(out/'postboot-collector.py').read_bytes();scope={};exec(compile(source,'<same-protocol-collector>','exec'),scope)
assert (raw/'worker.py').read_bytes()==(out/'pm-worker.py').read_bytes() and (raw/'supervisor.py').read_bytes()==(u.POST/'pm-smoke-supervisor.py').read_bytes()
terminal=read(raw/'worker-terminal-private.json');assert terminal['terminal'] and terminal['returncode']==0 and terminal['receipt_error'] is None and terminal['process']==read(raw/'worker-process-private.json')
for name in ['before-private.json','after-private.json']:
 value=read(raw/name);assert scope['audit'](value['raw'],request)==value['result'] and value['result']['passed'] and len(value['result']['checks'])==12 and not value['result']['errors']
result=read(raw/'result-private.json');assert result['device_functional_passed'] and result['terminal'] and result['transaction']['mem_write_attempts']==1
assert result['suspend_stats_delta']['success']==1 and result['suspend_stats_delta']['fail']==0 and not any(result['fault_delta'].values())
cleanup=read(raw/'trace-cleanup-private.json');trace_raw=(raw/'pm-wakeup-trace-private.txt').read_bytes();trace=trace_raw.decode()
assert cleanup['evidence']['sha256']==u.sha(trace_raw) and not cleanup['cleanup_errors'] and not cleanup['global_trace_modified'] and not cleanup['wakeup_policy_modified']
assert len(cleanup['evidence']['per_cpu'])==8
for stats in cleanup['evidence']['per_cpu'].values():
 for name in ['overrun','commit overrun','dropped events']:assert re.search(r'^'+name+r': 0$',stats,re.M)
suspend=trace.split('suspend_resume: dpm_prepare[2] begin',1)[1].split('suspend_resume: machine_suspend[1] end',1)[0]
assert 'wakeup_source_activate: samurai-usb-input' not in suspend and 'samurai_usb_complete' in trace.split('suspend_resume: dpm_complete[16] begin',1)[1]
callback=read(raw/'usb-callback-config-private.json');callback_cleanup=read(raw/'usb-callback-cleanup-private.json')
assert callback['filter']=='driver == "samurai-usb-input"' and set(callback['enable_readbacks'].values())=={'1'} and len(callback['enable_readbacks'])==2
assert not callback_cleanup['cleanup_errors'] and callback_cleanup['owned_instance_only']
for begin,end in [('dpm_suspend[2] begin','dpm_suspend[2] end'),('dpm_resume[16] begin','dpm_resume[16] end')]:
 phase=trace.split('suspend_resume: '+begin,1)[1].split('suspend_resume: '+end,1)[0]
 starts=[line for line in phase.splitlines() if 'device_pm_callback_start: samurai-usb-input ' in line]
 ends=[line for line in phase.splitlines() if 'device_pm_callback_end: samurai-usb-input ' in line]
 assert starts and ends and all(line.endswith('err=0') for line in ends), (begin,starts,ends)
launch=(out/'pm-launch/executed-source.py').read_bytes()
assert b'guard.parent.mkdir' not in launch and b'assert guard.read_bytes()' in launch
cache=read(out/'adoption-pointer.json')['protection_capture_cache_sha256']
code=('EXPECTED='+repr(request['new_boot_id'])+'\nCACHE='+repr(cache)+'\n').encode()+br'''
from pathlib import Path
import hashlib,json
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==EXPECTED
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert Path('/sys/class/power_supply/samurai-gauge-protection/health').read_text().strip()=='Good'
assert Path('/sys/class/power_supply/samurai-usb-input/input_current_limit').read_text().strip()=='500000'
assert hashlib.sha256(Path('/sys/devices/platform/samurai-gauge-protection/mac_evidence').read_bytes()).hexdigest()==CACHE
assert not Path('/sys/class/rtc/rtc0/wakealarm').read_text().strip() and not Path('/sys/kernel/tracing/instances/pm504-charger-timer-live-20261024-01').exists()
guard=Path('/var/lib/samurai/irq-native-usb-pm-activate-timer-20261024-01-adopted/boot-id-private.txt');assert guard.read_bytes()==(EXPECTED+'\n').encode()
print(json.dumps(dict(boot_id=EXPECTED,source500=True,health='Good',cache_preserved=True,alarm_empty=True,trace_removed=True,guard_reused=True)))
'''
fresh=u.call('pm-closeout',code)
public=dict(passed=True,current_cohort='Image504/USB13f41/chargerbef4/protectionf6bef/service83469/manifestf15e',boot_id=request['new_boot_id'],
 RTC_single_residency_seconds=result['transaction']['estimated_residency_seconds'],original_worker_terminal0=True,before_after_twelve_checks=True,
 USB_original_key_NCM_restored_without_replug=True,native_and_physical_input_ua=500000,current_cache_preserved=True,
 no_USB_software_wakeup_during_entry=True,software_notify_observed_in_complete=True,trace_no_loss_all8=True,own_alarm_and_trace_cleaned=True,
 existing_adoption_guard_reused=True,existing_guard_revalidated=True,
 USB_suspend_resume_callbacks_returned0=True,IRQ_arm_disarm_success_inferred_from_callback_source_and_runtime_policy=True,
 transaction_result=result,physical_USB_wakeup_accepted=False,whole_device_PM_accepted=False,
 evidence=dict(private_directory=str(out),worker_sha256=u.sha((raw/'worker.py').read_bytes()),trace_sha256=u.sha(trace_raw),result_sha256=u.sha((raw/'result-private.json').read_bytes())))
u.save(u.ROOT/'reference/charging-management-20261023/charger-timer-rtc001-result.json',public)
pointer=u.BASE/'boot-adoption-private.json';prior=(out/'adoption-pointer.json').read_bytes();assert pointer.read_bytes()==prior
current=json.loads(prior);current.update(PM_suspend_resume_verified=True,PM_single_RTC_residency_seconds=public['RTC_single_residency_seconds'],
 PM_current_protection_profile_verified=True,PM_current_USB_irq_wake_cohort_verified=True,PM_current_charger_timer_cohort_verified=True,USB_original_key_recovery_verified=True,PM_result_sha256=u.sha((u.ROOT/'reference/charging-management-20261023/charger-timer-rtc001-result.json').read_bytes()))
u.save(out/'adoption-pointer-after-pm.json',current);temp=u.BASE/'charger-timer-rtc-next-private.json';u.create(temp,(json.dumps(current,indent=2)+'\n').encode());assert pointer.read_bytes()==prior;temp.replace(pointer)
fd=os.open(pointer.parent,os.O_RDONLY|os.O_DIRECTORY)
try:os.fsync(fd)
finally:os.close(fd)
print(json.dumps(dict(passed=True,RTC_seconds=public['RTC_single_residency_seconds'],adopted_current_PM=True)))
