"""Adapt the prior observed-action GUI test to this boot and fresh output paths."""
from pathlib import Path
import ast,hashlib,json,shlex
import host
R=Path(__file__).resolve().parent
worker=(R.parent/'kernel268/native-snapshot-gui-r5.py').read_text()
old="system_services=json.loads((root/'k268-services-current-private.json').read_text())['new_processes']"
new="system_services=[dict(name=p['comm'],pid=p['pid'],start_ticks=p['start_ticks']) for p in json.loads((root/'k269-services-current-private.json').read_text())['processes'] if p['comm'] in ['pipewire','wireplumber']]"
assert worker.count(old)==1;worker=worker.replace(old,new)
worker=worker.replace("root/'k267-work/boot-id-private.txt'","root/'k269-work/boot-id-private.txt'")
worker=worker.replace('k268-snapshot-gui-r5','k270-snapshot-gui-r1').replace('k268_snapshot_gui_r5','k270_snapshot_gui_r1')
worker=worker.replace('/var/lib/samurai/k268-tools/gui-auto-r5.py','/var/lib/samurai/k270-tools/gui-auto-r1.py').replace('stage=268','stage=270')
controller=(R.parent/'kernel268/gui-auto-r5.py').read_text().replace('k268-snapshot-gui-r5','k270-snapshot-gui-r1')
(R/'native-snapshot-gui.py').write_text(worker);(R/'gui-auto.py').write_text(controller)
setup=r'''
from pathlib import Path
import hashlib,json,os,pwd,subprocess,sys,time
out=Path('/var/lib/samurai/k270-tools');out.mkdir(mode=0o700)
p=out/'gui-auto-r1.py';p.write_bytes(sys.stdin.buffer.read())
desktop=next(p for p in Path('/proc').glob('[0-9]*') if (p/'comm').exists() and (p/'comm').read_text().strip()=='phosh')
env={k.decode():v.decode() for x in (desktop/'environ').read_bytes().split(b'\0') if b'=' in x for k,v in [x.split(b'=',1)]}
u=pwd.getpwuid(10000)
def demote():os.initgroups(u.pw_name,u.pw_gid);os.setgid(u.pw_gid);os.setuid(u.pw_uid)
q=subprocess.run(['gdbus','call','--session','--dest','org.gnome.ScreenSaver','--object-path','/org/gnome/ScreenSaver','--method','org.gnome.ScreenSaver.SetActive','false'],env=env,preexec_fn=demote,capture_output=True,timeout=5)
assert q.returncode==0;time.sleep(1)
q=subprocess.run(['gdbus','call','--session','--dest','org.gnome.ScreenSaver','--object-path','/org/gnome/ScreenSaver','--method','org.gnome.ScreenSaver.GetActive'],env=env,preexec_fn=demote,capture_output=True,timeout=5)
assert q.returncode==0 and q.stdout.strip()==b'(false,)','Session remains locked or inactive; do not bypass it'
print(json.dumps(dict(controller_uploaded=True,standard_screen_wake=True,session_active=True)))
'''
q=host.ssh('python3 -c '+shlex.quote(setup),input=controller.encode(),timeout=20)
print(q.stdout.decode(),flush=True)
q=host.ssh('python3 -',input=worker.encode(),timeout=125,check=False)
(host.PRIVATE/'snapshot-gui-r1-response-private.log').write_bytes(q.stdout+q.stderr)
assert q.stdout,'Read the existing worker and boot state; do not replay the transaction'
d=json.loads(q.stdout)
for photo in (d.get('gui_control') or {}).get('new_jpegs',[]):photo.pop('path',None)
(R/'snapshot-gui-r1-validation.json').write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps(dict(completed=d['diagnostic_completed'],app_exit=d['app_exit_code'],controller_exit=d.get('controller_exit_code'),
 gui=d.get('gui_control'),fault_delta=d['fault_delta'],cleanup_errors=d['restore_errors'],camera_suspended=d['camera_devices_suspended']),indent=2))
assert q.returncode==0 and d['diagnostic_completed']
