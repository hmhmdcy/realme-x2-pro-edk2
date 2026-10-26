"""Inspect exact installed launch files and Phosh's camera setting before edits."""
from pathlib import Path
import json
import host
R=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json,os,pwd,subprocess
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
last=json.loads((r/'k240-snapshot-mmap/summary.json').read_text());assert last['diagnostic_completed'] and last['camera_devices_suspended'] and not any(last['fault_delta'].values())
out=r/'k240-snapshot-launcher-audit';assert not out.exists();out.mkdir(mode=0o700)
files={}
for rel in ['applications/org.gnome.Snapshot.desktop','dbus-1/services/org.gnome.Snapshot.service']:
 p=Path('/usr/share')/rel;assert p.is_file();files[rel]=p.read_text()
(out/'original-launch-files-private.json').write_text(json.dumps(files,indent=2)+'\n')
u=pwd.getpwuid(10000)
def demote():os.initgroups(u.pw_name,u.pw_gid);os.setgid(u.pw_gid);os.setuid(u.pw_uid)
env=dict(PATH='/usr/sbin:/usr/bin:/sbin:/bin',HOME=u.pw_dir,XDG_RUNTIME_DIR='/run/user/10000',DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/10000/bus')
inner=r"""
import gi,json
from gi.repository import Gio
source=Gio.SettingsSchemaSource.get_default();found={}
for name in ['sm.puri.phosh','sm.puri.phosh.phone-shell','sm.puri.phosh.plugins']:
 schema=source.lookup(name,True)
 if schema:
  settings=Gio.Settings.new(name)
  found[name]={k:settings.get_value(k).print_(True) for k in schema.list_keys() if 'camera' in k}
print(json.dumps(found))
"""
p=subprocess.run(['/usr/bin/python3','-c',inner],env=env,preexec_fn=demote,capture_output=True,timeout=10)
(out/'phosh-camera-settings-private.json').write_bytes(p.stdout);(out/'stderr-private.txt').write_bytes(p.stderr)
assert p.returncode==0
report=dict(stage=240,launch_files=files,phosh_camera_settings=json.loads(p.stdout),
 existing_user_overrides={rel:(Path(u.pw_dir)/'.local/share'/rel).exists() for rel in files},no_mutation=True)
(out/'summary-private.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=20)
(host.PRIVATE/'snapshot-launcher-audit-private.json').write_bytes(p.stdout)
print(p.stdout.decode())
