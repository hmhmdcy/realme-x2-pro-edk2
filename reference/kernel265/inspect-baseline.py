"""Revalidate live packages/daemons and enumerate standard camera devices without streaming."""
from pathlib import Path
import json,shlex
import host
R=Path(__file__).parent
provider=r'''
import json,time,gi
gi.require_version('Gst','1.0')
from gi.repository import Gst,GLib
Gst.init(None);p=Gst.DeviceProviderFactory.find('pipewiredeviceprovider').get();assert p.start()
try:
 c=GLib.MainContext.default();until=time.monotonic()+4
 while time.monotonic()<until:
  while c.pending():c.iteration(False)
  time.sleep(.02)
 devices=[]
 for d in p.get_devices():
  properties=d.get_properties();keys=['node.name','node.description','node.reliable','node.reliable.broadcast','api.libcamera.location','api.libcamera.model','device.api','media.class']
  devices.append(dict(name=d.get_display_name(),caps=d.get_caps().to_string(),properties={k:str(properties.get_value(k)) for k in keys if properties.has_field(k)}))
 print(json.dumps(devices))
finally:p.stop()
'''
code=r'''
from pathlib import Path
import hashlib,json,os,pwd,subprocess,sys
provider=sys.stdin.read();root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k260-work/boot-id-private.txt').read_bytes()
expected={'/usr/lib/libpipewire-0.3.so.0.1609.0':'870b7077747b14c74f15856a20f6ab93d68fde60703e0c116e2a9a38a8f91416','/usr/lib/spa-0.2/libcamera/libspa-libcamera.so':'0c3471e63587b6e930d712c8962464d636e18f2e36925ce85bb91f7349e8a9a8','/usr/lib/gstreamer-1.0/libgstpipewire.so':'d7a5500688d2881d04bc04c614eb46f00da7070bb96224c7f43f97b3a0e22935'}
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==digest for p,digest in expected.items())
services=json.loads((root/'k264-services-current-private.json').read_text())['new_processes']
for i in services:
 p=Path('/proc',str(i['pid']));assert (p/'stat').read_text().rsplit(')',1)[1].split()[19]==i['start_ticks']
 assert '/usr/lib/libpipewire-0.3.so.0.1609.0' in (p/'maps').read_text()
devices=['/sys/bus/i2c/devices/7-0010','/sys/bus/i2c/devices/9-0010','/sys/bus/platform/devices/ac4a000.cci','/sys/bus/platform/devices/ac4b000.cci','/sys/bus/platform/devices/acb3000.camss']
assert all(Path(p,'power/runtime_status').read_text().strip()=='suspended' for p in devices)
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
phosh=[p for p in Path('/proc').glob('[0-9]*') if (p/'comm').exists() and (p/'comm').read_text().strip()=='phosh'];assert len(phosh)==1;p=phosh[0]
raw={k.decode():v.decode() for x in (p/'environ').read_bytes().split(b'\0') if b'=' in x for k,v in [x.split(b'=',1)]}
env={k:v for k,v in raw.items() if k in ['HOME','USER','LOGNAME','LANG','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS','WAYLAND_DISPLAY','DISPLAY']};env['PATH']='/usr/sbin:/usr/bin:/sbin:/bin'
assert not any((q/'comm').exists() and (q/'comm').read_text().strip() in ['snapshot','megapixels'] for q in Path('/proc').glob('[0-9]*'))
user=pwd.getpwuid(10000)
def demote():os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
q=subprocess.run(['/usr/bin/python3','-'],input=provider.encode(),env=env,preexec_fn=demote,capture_output=True,timeout=10);assert q.returncode==0,q.stderr.decode()
items=json.loads(q.stdout);assert all(Path(p,'power/runtime_status').read_text().strip()=='suspended' for p in devices)
controls={}
for node in Path('/sys/class/video4linux').glob('v4l-subdev*'):
 name=(node/'name').read_text().strip()
 if name.startswith(('imx319','imx471')):controls[name]=subprocess.check_output(['v4l2-ctl','-d','/dev/'+node.name,'--list-ctrls']).decode()
report=dict(stage=265,current260_boot_verified=True,production_common_hashes_verified=True,service_identities=services,phosh=dict(pid=int(p.name),start_ticks=(p/'stat').read_text().rsplit(')',1)[1].split()[19]),standard_devices=items,controls=controls,camera_devices_suspended=True,taint=0,gpu_fault_count=subprocess.check_output(['dmesg']).count(b'gpu fault:'))
print(json.dumps(report))
'''
wrapper='import sys;source='+repr(code)+';exec(compile(source,"k265-inspect","exec"))'
q=host.ssh('python3 -c '+shlex.quote(wrapper),input=provider.encode(),timeout=20,check=False);(host.PRIVATE/'inspect-private.log').write_bytes(q.stdout+q.stderr)
assert q.returncode==0,'Inspect saved inventory failure before proceeding'
d=json.loads(q.stdout);(R/'baseline-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps({k:v for k,v in d.items() if k not in ['standard_devices','controls']},indent=2));print(json.dumps([dict(name=x['name'],properties=x['properties'],caps_entries=x['caps'].count(';')+1) for x in d['standard_devices']],indent=2))
