"""Verify that real session D-Bus activation inherits the per-app CPU flags."""
from pathlib import Path
import json
import host
R=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json,os,pwd,signal,subprocess,time
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
assert json.loads((r/'k240-snapshot-launcher-transaction/state-private.json').read_text())['state']=='verified'
out=r/'k240-snapshot-dbus-activation-r2';assert not out.exists();out.mkdir(mode=0o700)
u=pwd.getpwuid(10000)
def demote():os.initgroups(u.pw_name,u.pw_gid);os.setgid(u.pw_gid);os.setuid(u.pw_uid)
desktop=[]
for q in Path('/proc').glob('[0-9]*'):
 try:
  if (q/'comm').read_text().strip()=='phosh' and int((q/'status').read_text().split('Uid:',1)[1].split()[0])==10000:desktop.append(q)
 except OSError:pass
assert len(desktop)==1
actual_session={k.decode():v.decode() for x in (desktop[0]/'environ').read_bytes().split(b'\0') if b'=' in x for k,v in [x.split(b'=',1)]}
env={k:v for k,v in actual_session.items() if k in ['HOME','USER','LOGNAME','LANG','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS','WAYLAND_DISPLAY','DISPLAY','XDG_DATA_DIRS','XDG_CONFIG_DIRS']}
env.update(PATH='/usr/sbin:/usr/bin:/sbin:/bin',HOME=u.pw_dir);assert 'DBUS_SESSION_BUS_ADDRESS' in env
inner=r"""
import dbus,json
b=dbus.SessionBus(private=True);d=dbus.Interface(b.get_object('org.freedesktop.DBus','/org/freedesktop/DBus'),'org.freedesktop.DBus')
existing=bool(d.NameHasOwner('org.gnome.Snapshot'))
result=int(d.StartServiceByName('org.gnome.Snapshot',0)) if not existing else 2
owner=str(d.GetNameOwner('org.gnome.Snapshot'));pid=int(d.GetConnectionUnixProcessID(owner))
print(json.dumps(dict(existing=existing,start_result=result,pid=pid)));b.close()
"""
before=subprocess.check_output(['dmesg'],timeout=5)
p=subprocess.run(['/usr/bin/python3','-c',inner],env=env,preexec_fn=demote,capture_output=True,timeout=20)
(out/'activation-private.json').write_bytes(p.stdout);(out/'stderr-private.txt').write_bytes(p.stderr);assert p.returncode==0
data=json.loads(p.stdout);proc=Path('/proc',str(data['pid']));ticks=(proc/'stat').read_text().rsplit(')',1)[1].split()[19]
assert os.readlink(proc/'exe')=='/usr/bin/snapshot' and int((proc/'status').read_text().split('Uid:',1)[1].split()[0])==10000
actual={k.decode():v.decode() for x in (proc/'environ').read_bytes().split(b'\0') if b'=' in x for k,v in [x.split(b'=',1)]}
flags={k:actual.get(k) for k in ['GSK_RENDERER','GDK_DISABLE']};(out/'actual-cpu-flags.json').write_text(json.dumps(flags,indent=2)+'\n')
good=flags==dict(GSK_RENDERER='cairo',GDK_DISABLE='gl,vulkan,offload')
nodes=['/sys/bus/i2c/devices/7-0010','/sys/bus/i2c/devices/9-0010','/sys/bus/platform/devices/acb3000.camss']
idle=all(Path(n,'power/runtime_status').read_text().strip()=='suspended' for n in nodes)
stopped=False
if not data['existing'] and data['start_result']==1 and idle:
 os.kill(data['pid'],signal.SIGTERM);deadline=time.monotonic()+5
 while proc.exists() and (proc/'stat').read_text().rsplit(')',1)[1].split()[19]==ticks and time.monotonic()<deadline:time.sleep(.05)
 stopped=not proc.exists() or (proc/'stat').read_text().rsplit(')',1)[1].split()[19]!=ticks
after=subprocess.check_output(['dmesg'],timeout=5)
faults={k:after.count(v)-before.count(v) for k,v in dict(gpu=b'gpu fault:',warning=b'WARNING:',oops=b'Oops:').items()}
report=dict(stage=240,real_user_session_dbus_activation_verified=good,preexisting_snapshot_preserved=data['existing'],
 newly_started_service_without_window_requested=not data['existing'],own_idle_service_stopped=stopped,
 actual_cpu_flags=flags,camera_idle_before_own_service_stop=idle,no_activate_or_shutter_called=True,fault_delta=faults,
 taint=int(Path('/proc/sys/kernel/tainted').read_text()))
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));assert good and not any(faults.values())
'''
p=host.ssh('python3 -',input=code.encode(),timeout=35)
(host.PRIVATE/'snapshot-dbus-verify-host-private.log').write_bytes(p.stdout+p.stderr)
data=json.loads(p.stdout);(R/'snapshot-dbus-activation-validation.json').write_text(json.dumps(data,indent=2)+'\n')
print(json.dumps(data))
