"""Read PipeWire camera exports and simulate a matching full camera application."""
from pathlib import Path
import json
import host

R=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json,os,pwd,shutil,subprocess
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k236-runtime/boot-id-private.txt').read_bytes()
assert json.loads((root/'k240-megapixels-startup/state-private.json').read_text())['state']=='terminal'
out=root/'k240-libcamera-gui-audit-r2';assert not out.exists();out.mkdir(mode=0o700)
user=pwd.getpwuid(10000)
def demote():os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
env=dict(PATH='/usr/bin:/bin',HOME=user.pw_dir,XDG_RUNTIME_DIR='/run/user/10000')
pw_available=bool(shutil.which('pw-dump'));objects=[];cameras=[]
if pw_available:
 p=subprocess.run(['pw-dump'],env=env,preexec_fn=demote,capture_output=True,timeout=12)
 (out/'pipewire-private.json').write_bytes(p.stdout);(out/'pipewire-stderr-private.txt').write_bytes(p.stderr)
 assert p.returncode==0;objects=json.loads(p.stdout)
for item in objects:
 props=(item.get('info') or {}).get('props',{})
 if props.get('media.class','').startswith('Video/'):
  cameras.append(dict(object_id=item.get('id'),type=item.get('type'),state=item.get('info',{}).get('state'),
   properties={k:v for k,v in props.items() if k in ['node.name','node.description','device.name','device.description','device.api','media.class','factory.name','api.libcamera.camera.id','api.libcamera.camera.location']},
   params=item.get('info',{}).get('params',{})))
(out/'pipewire-cameras-private.json').write_text(json.dumps(cameras,indent=2)+'\n')
p=subprocess.run(['apk','add','--simulate','snapshot'],capture_output=True,text=True,timeout=45)
(out/'snapshot-simulation-private.log').write_text(p.stdout+p.stderr)
actions=[line for line in p.stdout.splitlines() if line.startswith('(')]
report=dict(stage=240,pw_dump_available=pw_available,pipewire_camera_nodes=len(cameras) if pw_available else None,cameras=[{k:v for k,v in c.items() if k not in ['params','object_id']} for c in cameras],
 snapshot_simulation_exit=p.returncode,package_actions=actions,
 simulation_tail=(p.stdout+p.stderr).splitlines()[-12:],no_package_transaction=True,
 no_camera_capture_or_shutter=True,megapixels_diagnostic_terminal=True)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
'''
result=host.ssh('python3 -',input=code.encode(),timeout=70)
(host.PRIVATE/'libcamera-gui-audit-host-private.log').write_bytes(result.stdout+result.stderr)
report=json.loads(result.stdout)
(R/'libcamera-gui-audit-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
