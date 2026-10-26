"""Read the actual session's GStreamer PipeWire camera provider; no stream."""
from pathlib import Path
import json
import host

R = Path(__file__).resolve().parent
code = r'''
from pathlib import Path
import json,os,pwd,subprocess
root=Path('/var/lib/samurai')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k236-runtime/boot-id-private.txt').read_bytes()
assert json.loads((root/'k240-snapshot-app-transaction/summary.json').read_text())['all944_previous_package_records_unchanged']
out=root/'k240-snapshot-provider';assert not out.exists();out.mkdir(mode=0o700)
user=pwd.getpwuid(10000)
desktop=[]
for p in Path('/proc').glob('[0-9]*'):
 try:
  if (p/'comm').read_text().strip()=='phosh' and int((p/'status').read_text().split('Uid:',1)[1].split()[0])==10000:desktop.append(p)
 except OSError:pass
assert len(desktop)==1
inherited={k.decode():v.decode() for x in (desktop[0]/'environ').read_bytes().split(b'\0') if b'=' in x for k,v in [x.split(b'=',1)]}
keys=['HOME','USER','LOGNAME','LANG','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS','WAYLAND_DISPLAY','DISPLAY','XDG_DATA_DIRS','XDG_CONFIG_DIRS']
env={k:v for k,v in inherited.items() if k in keys or k.startswith(('GDK_','GSK_','GTK_','MESA_'))}
env.update(PATH='/usr/sbin:/usr/bin:/sbin:/bin',HOME=user.pw_dir)
assert all(k in env for k in ['XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS','WAYLAND_DISPLAY'])
def demote():os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
inner=r"""
import gi,json,time
gi.require_version('Gst','1.0')
from gi.repository import Gst,GLib
Gst.init(None)
factory=Gst.DeviceProviderFactory.find('pipewiredeviceprovider')
assert factory is not None,'PipeWire Gst device provider unavailable'
provider=factory.get();assert provider is not None
started=provider.start();assert started
try:
 ctx=GLib.MainContext.default();deadline=time.monotonic()+6
 while time.monotonic()<deadline:
  while ctx.pending():ctx.iteration(False)
  time.sleep(.05)
 devices=[]
 for d in provider.get_devices():
  p=d.get_properties();c=d.get_caps()
  props={p.nth_field_name(i):str(p.get_value(p.nth_field_name(i))) for i in range(p.n_fields())} if p else {}
  devices.append(dict(display_name=d.get_display_name(),device_class=d.get_device_class(),properties=props,caps=c.to_string() if c else None))
 print(json.dumps(dict(provider_started=bool(started),devices=devices)),flush=True)
finally:provider.stop()
"""
p=subprocess.run(['/usr/bin/python3','-c',inner],env=env,preexec_fn=demote,capture_output=True,timeout=20)
(out/'provider-stdout-private.json').write_bytes(p.stdout);(out/'provider-stderr-private.txt').write_bytes(p.stderr)
assert p.returncode==0,'Provider query failed; see private receipts'
data=json.loads(p.stdout)
g=subprocess.run(['gsettings','get','org.gnome.Snapshot','last-camera-id'],env=env,preexec_fn=demote,capture_output=True,timeout=6)
(out/'gsettings-last-camera-before-private.txt').write_bytes(g.stdout);(out/'gsettings-stderr-private.txt').write_bytes(g.stderr)
assert g.returncode==0
for group in ['v4l2/vb2_v4l2_buf_done','v4l2/vb2_v4l2_dqbuf','vb2/vb2_buf_done']:
 f=Path('/sys/kernel/tracing/events',group,'format')
 if f.exists():(out/('trace-format-'+group.replace('/','-')+'.txt')).write_text(f.read_text())
devices=['7-0010','9-0010']
report=dict(stage=240,provider_started=data['provider_started'],camera_count=len(data['devices']),
 cameras=[dict(display_name=x['display_name'],device_class=x['device_class'],caps=x['caps'],properties={k:v for k,v in x['properties'].items() if k in ['device.api','node.name','node.description','media.class','object.path','api.libcamera.camera.id','api.libcamera.camera.location']}) for x in data['devices']],
 sensor_runtime_status={b:Path('/sys/bus/i2c/devices',b,'power/runtime_status').read_text().strip() for b in devices},
 gsettings_read=True,no_camera_stream_or_shutter=True,taint=int(Path('/proc/sys/kernel/tainted').read_text()))
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
'''
result=host.ssh('python3 -',input=code.encode(),timeout=35)
(host.PRIVATE/'snapshot-provider-host-private.log').write_bytes(result.stdout+result.stderr)
data=json.loads(result.stdout)
(R/'snapshot-provider-validation.json').write_text(json.dumps(data,indent=2)+'\n')
print(json.dumps(data))
