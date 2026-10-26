"""Add the tested opt-in flag to the two existing per-user camera launchers."""
from pathlib import Path
import hashlib,json,shlex
import host
R=Path(__file__).parent;ROOT=R.parents[1]
system=json.loads((R/'flow-4000000-validation.json').read_text())
assert system['buffer_not_recycled']==0 and system['summary']['diagnostic_completed']
proof=json.loads((R/'package-install-validation.json').read_text())
expected={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'linux-port/camera/snapshot-launcher').iterdir() if p.is_file()}
code=r'''
from pathlib import Path
import hashlib,json,os,pwd,subprocess,sys
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k260-work/boot-id-private.txt').read_bytes()
expected,proof=json.loads(sys.argv[1]);out=root/'k262-launcher-transaction';assert not out.exists();out.mkdir(mode=0o700)
assert hashlib.sha256(Path('/usr/lib/gstreamer-1.0/libgstpipewire.so').read_bytes()).hexdigest()==proof['plugin_sha256']
user=pwd.getpwuid(10000)
files=[Path(user.pw_dir)/'.local/share/applications/org.gnome.Snapshot.desktop',Path(user.pw_dir)/'.local/share/dbus-1/services/org.gnome.Snapshot.service']
needle='GDK_DISABLE=gl,vulkan,offload /usr/bin/snapshot'
entries=[]
for p in files:
 b=p.read_bytes();assert hashlib.sha256(b).hexdigest()==expected[p.name]
 assert b.decode().count(needle)==1
 entries.append((p,b,b.decode().replace(needle,'GDK_DISABLE=gl,vulkan,offload SAMURAI_CAMERA_COPY=1 /usr/bin/snapshot').encode()))
manifest=[]
for p,b,c in entries:
 (out/(p.name+'.before-private')).write_bytes(b)
 temporary=p.with_name(p.name+'.k262-new');assert not temporary.exists()
 temporary.write_bytes(c);temporary.chmod(p.stat().st_mode & 0o777);os.chown(temporary,p.stat().st_uid,p.stat().st_gid);os.replace(temporary,p)
 manifest.append(dict(file=p.name,before_sha256=hashlib.sha256(b).hexdigest(),after_sha256=hashlib.sha256(c).hexdigest()))
desktops=[]
for p in Path('/proc').glob('[0-9]*'):
 try:
  if (p/'comm').read_text().strip()=='phosh':desktops.append(p)
 except OSError:pass
assert len(desktops)==1
env={k.decode():v.decode() for x in (desktops[0]/'environ').read_bytes().split(b'\0') if b'=' in x for k,v in [x.split(b'=',1)]}
def demote():os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
p=subprocess.run(['gdbus','call','--session','--dest','org.freedesktop.DBus','--object-path','/org/freedesktop/DBus','--method','org.freedesktop.DBus.ReloadConfig'],env=env,preexec_fn=demote,capture_output=True,timeout=8)
(out/'reload-dbus-private.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0
lock=subprocess.run(['gdbus','call','--session','--dest','org.gnome.ScreenSaver','--object-path','/org/gnome/ScreenSaver','--method','org.gnome.ScreenSaver.GetActive'],env=env,preexec_fn=demote,capture_output=True,timeout=8)
report=dict(stage=262,installed=True,copy_opt_in='SAMURAI_CAMERA_COPY=1',launcher_files=manifest,session_dbus_reload_passed=True,global_desktop_environment_changed=False,snapshot_gui_activated=False,screen_lock_query=lock.stdout.decode().strip(),gui_preview_acceptance_pending=True)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(report=report,contents={p.name:p.read_text() for p in files})))
'''
r=host.ssh('python3 - '+shlex.quote(json.dumps([expected,proof])),input=code.encode(),timeout=25)
(host.PRIVATE/'launcher-install-private.json').write_bytes(r.stdout)
d=json.loads(r.stdout)
for name,content in d['contents'].items():(ROOT/'linux-port/camera/snapshot-launcher'/name).write_text(content)
(R/'launcher-install-validation.json').write_text(json.dumps(d['report'],indent=2)+'\n')
print(json.dumps(d['report']))
