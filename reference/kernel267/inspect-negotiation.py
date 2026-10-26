"""Inspect advertised formats and ordinary service diagnostics after negotiation failure."""
from pathlib import Path
import json
import host

code=r'''
from pathlib import Path
import json,os,pwd,subprocess
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k267-work/boot-id-private.txt').read_bytes()
user=pwd.getpwuid(10000)
desktop=next(p for p in Path('/proc').glob('[0-9]*') if (p/'comm').exists() and (p/'comm').read_text().strip()=='phosh')
inherited={k.decode():v.decode() for item in (desktop/'environ').read_bytes().split(b'\0') if b'=' in item for k,v in [item.split(b'=',1)]}
env={k:v for k,v in inherited.items() if k in ['PATH','HOME','USER','LOGNAME','LANG','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS','WAYLAND_DISPLAY']}
def demote():os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
probe="""
import gi,json,time
gi.require_version('Gst','1.0')
from gi.repository import Gst,GLib
Gst.init(None);p=Gst.DeviceProviderFactory.get_by_name('pipewiredeviceprovider');p.start();t=time.monotonic()+3
while time.monotonic()<t:
 while GLib.MainContext.default().pending():GLib.MainContext.default().iteration(False)
 time.sleep(.02)
print(json.dumps([dict(name=d.get_display_name(),properties=d.get_properties().to_string(),caps=d.get_caps().to_string()) for d in p.get_devices()]))
p.stop()
"""
q=subprocess.run(['python3','-c',probe],env=env,preexec_fn=demote,capture_output=True,timeout=10)
result=dict(provider_stdout=q.stdout.decode(),provider_stderr=q.stderr.decode(),logs={})
for item in json.loads((r/'k267-services-current-private.json').read_text())['new_processes']:
 p=Path('/proc',str(item['pid']));fds={n:os.readlink(p/'fd'/n) for n in ['1','2']};result['logs'][item['name']]=dict(fd_targets=fds)
 for n,target in fds.items():
  path=Path(target)
  if path.is_absolute() and path.is_file() and not str(path).startswith('/dev'):
   with path.open('rb') as stream:
    stream.seek(max(0,path.stat().st_size-40000));result['logs'][item['name']]['tail_'+n]=stream.read().decode(errors='replace')
result['cam_stdout']=(r/'k267-native-cam/0-rear-stdout-private.txt').read_text()
result['cam_stderr']=(r/'k267-native-cam/0-rear-stderr-private.txt').read_text()
print(json.dumps(result))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=25)
(host.PRIVATE/'negotiation-private.json').write_bytes(q.stdout)
d=json.loads(q.stdout)
print(d['provider_stdout']);print(d['cam_stdout'][:1300]);print(d['cam_stderr'][-1600:])
for n,row in d['logs'].items():
 print(n+': '+json.dumps(row['fd_targets']))
 for key,value in row.items():
  if key.startswith('tail_'):print(value[-5000:])
