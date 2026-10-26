"""Bounded standard INHIBIT/AUTO transition; observe without polling the gauge."""
from pathlib import Path
import importlib.util
import json
import shlex

ref = Path(__file__).resolve().parent
out = Path('/mnt/e/edk2-samurai-out/charging-management-20261023/runtime-notifications')
out.mkdir(exist_ok=True)
with (out / 'request.json').open('x') as f: json.dump({'count': 1}, f)
spec = importlib.util.spec_from_file_location('window', ref / 'device-window.py')
window = importlib.util.module_from_spec(spec); spec.loader.exec_module(window)
code = '''from pathlib import Path
import hashlib,importlib.util,json,os,runpy,subprocess,time,traceback
os.umask(0o077);d=Path('/root/charging-management-20261023/runtime-notifications');d.mkdir(mode=0o700)
manager=runpy.run_path('/usr/sbin/samurai-charging');manager['verify']();live=manager['live']
assert hashlib.sha256(Path('/usr/share/samurai-charging/manifest.json').read_bytes()).hexdigest()=='f1a885e2ca9c3226ca50d94f39c17c3cae5411b1047696976975df976aa971cf'
spec=importlib.util.spec_from_file_location('events',d.parent/'usb-reenumerate/events.py');events=importlib.util.module_from_spec(spec);spec.loader.exec_module(events)
spec=importlib.util.spec_from_file_location('health',d.parent/'usb-reenumerate/health.py');health=importlib.util.module_from_spec(spec);spec.loader.exec_module(health)
before_camera,before_log=health.camera_state(),health.log_counts()
psy=live.PSY/'mp2650-input';behaviour=psy/'charge_behaviour'
assert '[auto]' in behaviour.read_text()
limits={n:(psy/n).read_text() for n in ['input_current_limit','constant_charge_current','constant_charge_voltage']}
start=time.monotonic();realtime=time.time();ui=events.UIEvents(d,start);rows=[];actions=[];failure=None
def observe(seconds,phase):
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  rows.append({'t':time.monotonic()-start,'phase':phase,'sample':manager['sample'](),'registers':live.registers()})
  time.sleep(.5)
try:
 observe(10,'stable-auto')
 actions.append({'t':time.monotonic()-start,'action':'inhibit-charge'});behaviour.write_text('inhibit-charge')
 observe(6,'inhibit')
 actions.append({'t':time.monotonic()-start,'action':'auto'});behaviour.write_text('auto')
 observe(10,'restored-auto')
except BaseException:failure=traceback.format_exc()
finally:
 if '[auto]' not in behaviour.read_text():behaviour.write_text('auto')
 ui.stop()
last=manager['sample']();final_log=health.log_counts()
healthy=last['valid']==last['online']==last['protection_ok']==last['desired_enable']==1 and not any(last[k] for k in ['error','stop_error','latched','source_inhibit','fault'])
steady=[e for e in ui.events if e.get('POWER_SUPPLY_NAME')=='mp2650-input' and 2<e['t']<10]
inhibited=[r for r in rows if r['phase']=='inhibit' and not r['sample']['desired_enable'] and r['registers']['08']&0x18==8]
faults={k:final_log[k]-before_log[k] for k in before_log}
result={'passed':not failure and healthy and len(inhibited)>=3 and len(steady)<=1 and not any(faults.values()) and before_camera==health.camera_state() and int(Path('/proc/sys/kernel/tainted').read_text())==0,
 'terminal':True,'duration_seconds':time.monotonic()-start,'stable_charger_events_2_to_10s':len(steady),'inhibited_samples':len(inhibited),'restored_healthy':healthy,
 'limits_unchanged':limits=={n:(psy/n).read_text() for n in limits},'native_allowance_ua':int((live.PSY/'samurai-usb-input/input_current_limit').read_text()),
 'taint':int(Path('/proc/sys/kernel/tainted').read_text()),'camera_and_four_services_unchanged':before_camera==health.camera_state(),'fault_delta':faults,
 'physical_icon_acceptance':False,'observer_polled_battery_status':False,'manifest_sha256':hashlib.sha256(Path('/usr/share/samurai-charging/manifest.json').read_bytes()).hexdigest()}
capture={'result':result,'rows':rows,'actions':actions,'start_realtime':realtime,'kernel_events':ui.events,'upower_dbus_log':(d/'upower-dbus-private.log').read_text(),'failure':failure}
(d/'capture-private.json').write_text(json.dumps(capture));print(json.dumps(capture))
'''
(out / 'worker.py').write_text(code)
q = window.host.ssh('python3 -c ' + shlex.quote(code), timeout=55, check=False)
(out / 'capture-private.json').write_bytes(q.stdout)
(out / 'stderr-private.txt').write_bytes(q.stderr)
if q.returncode:
    print(q.stderr.decode(errors='replace')[-3000:]); raise SystemExit(q.returncode)
data = json.loads(q.stdout)
(ref / 'runtime-notification-result.json').write_text(json.dumps(data['result'], indent=2) + '\n')
print(json.dumps(data['result'], indent=2))
