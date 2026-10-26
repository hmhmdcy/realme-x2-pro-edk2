from pathlib import Path
import ast,hashlib,json,subprocess
import host

here=Path(__file__).resolve().parent;source=here/'samurai-gnss-assist.py'
ast.parse(source.read_text());digest=hashlib.sha256(source.read_bytes()).hexdigest()
dest='/var/lib/samurai/k202-helper-deploy'
host.ssh('test ! -e '+dest+' && mkdir -m700 '+dest)
host.upload(source,dest+'/candidate.py')
native=r'''
from pathlib import Path
import dbus,hashlib,json,os,subprocess,time
root=Path('/var/lib/samurai');out=root/'k202-helper-deploy';target=Path('/usr/sbin/samurai-gnss-assist')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k202-runtime/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#183 ') and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert hashlib.sha256(target.read_bytes()).hexdigest()=='cf3d92a46e619ceba30342fb2c063fb39ba9de5ddd2043e5dc0a5f59f39bef41'
bus=dbus.SystemBus(private=True);props=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/0'),'org.freedesktop.DBus.Properties')
assert int(props.Get('org.freedesktop.ModemManager1.Modem.Location','Enabled'))==0 and not bus.name_has_owner('org.freedesktop.GeoClue2')
power=int(props.Get('org.freedesktop.ModemManager1.Modem','PowerState'));assert power==1
state=json.loads((root/'gnss-assist/watch-state.json').read_text());assert state['running'] and not state['active'] and state['worker_starts']==state['worker_completions']==2
(out/'helper-before-private.py').write_bytes(target.read_bytes());(out/'watch-before-private.json').write_text(json.dumps(state,indent=2)+'\n')
subprocess.run(['rc-service','samurai-gnss-assist','stop'],check=True,capture_output=True,timeout=20)
assert not json.loads((root/'gnss-assist/watch-state.json').read_text())['running']
candidate=out/'candidate.py';assert hashlib.sha256(candidate.read_bytes()).hexdigest()=='DIGEST'
candidate.chmod(0o755);os.replace(candidate,target)
subprocess.run(['rc-service','samurai-gnss-assist','start'],check=True,capture_output=True,timeout=20)
deadline=time.monotonic()+70
while time.monotonic()<deadline:
 state=json.loads((root/'gnss-assist/watch-state.json').read_text())
 if state.get('time_prepared') and state['time_preparation_starts']==state['time_preparation_completions']==1:break
 time.sleep(1)
else:raise AssertionError('Inspect worker logs; time preparation not confirmed')
assert state['worker_starts']==state['worker_completions']==0 and not state['active'] and state['running']
assert state['source_sha256']=='DIGEST'
assert int(props.Get('org.freedesktop.ModemManager1.Modem.Location','Enabled'))==0 and int(props.Get('org.freedesktop.ModemManager1.Modem','PowerState'))==power
r=dict(stage=202,helper_sha256='DIGEST',atomic_install=True,previous_helper_and_state_backed_up=True,default_runlevel_preserved=Path('/etc/runlevels/default/samurai-gnss-assist').is_symlink(),idle_time_preparation=state['time_preparation_last_result'],idle_time_preparation_count=1,active_data_workers=0,gps_enabled=0,modem_power_state=power,cold_first_session_fix_not_yet_verified=True)
(out/'summary.json').write_text(json.dumps(r,indent=2)+'\n');bus.close();print(json.dumps(r))
'''.replace('DIGEST',digest)
try:p=host.ssh('python3 -',input=native.encode(),timeout=110)
except subprocess.CalledProcessError as e:
 (host.PRIVATE/'helper-deploy-failed-private.log').write_bytes((e.stdout or b'')+(e.stderr or b''));raise SystemExit('Helper deployment check failed; inspect private evidence')
(host.PRIVATE/'helper-deploy-private.json').write_bytes(p.stdout)
(here/'helper-deployment-validation.json').write_text(json.dumps(json.loads(p.stdout),indent=2)+'\n')
print(p.stdout.decode())
