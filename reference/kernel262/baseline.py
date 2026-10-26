"""Read current camera/session identity without starting a stream."""
from pathlib import Path
import json
import host

code = r'''
from pathlib import Path
import json,os,pwd,subprocess
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k260-work/boot-id-private.txt').read_bytes()
def cmd(args):
 if not __import__('shutil').which(args[0]):return dict(exit=127,stdout='',stderr='Command unavailable')
 p=subprocess.run(args,capture_output=True,text=True,timeout=10)
 return dict(exit=p.returncode,stdout=p.stdout,stderr=p.stderr)
procs=[];desktop=[]
for p in Path('/proc').glob('[0-9]*'):
 try:
  name=(p/'comm').read_text().strip()
  if name in ['snapshot','megapixels','pipewire','wireplumber','phosh']:
   procs.append(dict(name=name,pid=int(p.name),start_ticks=(p/'stat').read_text().rsplit(')',1)[1].split()[19]))
  if name=='phosh':desktop.append(p)
 except OSError:pass
assert len(desktop)==1
env={k.decode():v.decode() for x in (desktop[0]/'environ').read_bytes().split(b'\0') if b'=' in x for k,v in [x.split(b'=',1)]}
user=pwd.getpwuid(10000)
def demote():os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
locked=subprocess.run(['gdbus','call','--session','--dest','org.gnome.ScreenSaver','--object-path','/org/gnome/ScreenSaver','--method','org.gnome.ScreenSaver.GetActive'],env=env,preexec_fn=demote,capture_output=True,text=True,timeout=8)
paths=['/sys/bus/i2c/devices/7-0010','/sys/bus/i2c/devices/9-0010','/sys/bus/platform/devices/ac4a000.cci','/sys/bus/platform/devices/ac4b000.cci','/sys/bus/platform/devices/acb3000.camss']
dmesg=cmd(['dmesg'])['stdout']
report=dict(stage=262,current260_boot_verified=True,packages=cmd(['apk','info','-v']),processes=procs,lock_query=dict(exit=locked.returncode,result=locked.stdout.strip()),runtime={p:Path(p,'power/runtime_status').read_text().strip() for p in paths},taint=int(Path('/proc/sys/kernel/tainted').read_text()),gpu_fault_count=dmesg.count('gpu fault:'),camera_nodes={p.name:(p/'name').read_text().strip() for p in Path('/sys/class/video4linux').glob('*')},gst=cmd(['gst-inspect-1.0','pipewiresrc']),launcher={p.name:p.read_text() for p in [Path(user.pw_dir)/'.local/share/applications/org.gnome.Snapshot.desktop',Path(user.pw_dir)/'.local/share/dbus-1/services/org.gnome.Snapshot.service'] if p.exists()})
print(json.dumps(report))
'''
r=host.ssh('python3 -',input=code.encode(),timeout=50)
(host.PRIVATE/'baseline-private.json').write_bytes(r.stdout)
d=json.loads(r.stdout)
packages=d.pop('packages')
d['package_count']=len(packages['stdout'].splitlines())
d['camera_packages']=[s for s in packages['stdout'].splitlines() if s.startswith(('libcamera','pipewire','snapshot','gst-plugins-rs-gtk4','gtk4.0','samurai-camera'))]
gst=d.pop('gst');(host.PRIVATE/'gst-inspect-private.json').write_text(json.dumps(gst))
d['pipewiresrc_available']=gst['exit']==0
(Path(__file__).parent/'baseline-validation.json').write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps(d,indent=2))
