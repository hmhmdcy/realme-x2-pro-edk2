"""Read-only recovery snapshot after the user restored the USB connection."""
from pathlib import Path
import importlib.util
import json
import shlex

ref = Path(__file__).resolve().parent
out = Path('/mnt/e/edk2-samurai-out/charging-management-20261023/pm-r5-recovery')
out.mkdir(exist_ok=True)
spec = importlib.util.spec_from_file_location('window', ref / 'device-window.py')
window = importlib.util.module_from_spec(spec); spec.loader.exec_module(window)
code = '''from pathlib import Path
import hashlib,json,os,runpy,subprocess,time
manager=runpy.run_path('/usr/sbin/samurai-charging');meta=manager['verify']()
digest=hashlib.sha256(Path('/usr/share/samurai-charging/manifest.json').read_bytes()).hexdigest()
assert digest=='f1a885e2ca9c3226ca50d94f39c17c3cae5411b1047696976975df976aa971cf'
for name,entry in meta['modules'].items():manager['loaded_matches'](Path(entry['target']),name.replace('-','_'))
live=manager['live'];state=live.state();sample=manager['sample']()
base=Path('/root/charging-management-20261023/charging-pm-r5')
before=json.loads((base/'before-private.json').read_text())
pid=int(base.with_suffix('.pid').read_text());cmd=Path('/proc')/str(pid)/'cmdline'
argv=cmd.read_bytes().split(bytes([0])) if cmd.exists() else []
worker_alive=str(base.with_suffix('.py')).encode() in argv
log=subprocess.check_output(['dmesg'],text=True)
oldlog=(base/'dmesg-before-private.txt').read_text()
tokens=['WARNING:','Oops:','refcount_t: underflow','gpu fault:','NGD resume failed']
native=int((live.PSY/'samurai-usb-input/input_current_limit').read_text())
def optional_read(path):
 try:return {'value':Path(path).read_text().strip()}
 except OSError as e:return {'errno':e.errno}
healthy=(sample['valid']==sample['online']==sample['protection_ok']==sample['desired_enable']==1
 and sample['shadow']==0 and 0<=sample['age_ms']<2000
 and not any(sample[k] for k in ['error','stop_error','latched','source_inhibit','fault','cycle_timeout']))
same_camera=state['camera_pm']==before['camera_pm'] and state['m2m']==before['m2m'] and state['services']==before['services']
result={'worker_exited':not worker_alive,'terminal':json.loads((base/'runtime-result.json').read_text())['terminal'],
 'same_boot':state['boot_id']==before['boot_id'],'manifest_sha256':digest,'modules_exact':True,
 'charging_healthy':healthy,'native_allowance_ua':native,'taint':int(state['taint']),
 'camera_and_four_services_unchanged':same_camera,
 'fault_delta':{k:log.count(k)-oldlog.count(k) for k in tokens},
 'pm_wakeup_irq':optional_read('/sys/power/pm_wakeup_irq'),
 'rtc_alarm':Path('/sys/class/rtc/rtc0/wakealarm').read_text().strip(),
 'physical_icon_latency_accepted':False,'planned_rtc_pm_accepted':False}
result['restored']=bool(result['terminal'] and result['worker_exited'] and result['same_boot']
 and healthy and native==100000 and result['taint']==0 and same_camera and not any(result['fault_delta'].values()))
print(json.dumps({'result':result,'state':state,'sample':sample,'boot_id':state['boot_id'],
 'manifest':meta,'boottime':time.clock_gettime(time.CLOCK_BOOTTIME),'monotonic':time.monotonic(),
 'interrupts':Path('/proc/interrupts').read_text(),'dmesg':log}))
'''
q = window.host.ssh('python3 -c ' + shlex.quote(code), timeout=40, check=False)
(out / 'snapshot-private.json').write_bytes(q.stdout)
(out / 'stderr-private.txt').write_bytes(q.stderr)
if q.returncode:
    print(q.stderr.decode(errors='replace')[-2000:]); raise SystemExit(q.returncode)
data = json.loads(q.stdout)
(ref / 'pm-r5-recovery-result.json').write_text(json.dumps(data['result'], indent=2) + '\n')
print(json.dumps(data['result'], indent=2))
