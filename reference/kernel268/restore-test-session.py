"""Restore only our unchanged temporary startup overrides and lock settings."""
from pathlib import Path
import host,json
code=r'''
from pathlib import Path
import hashlib,json,os,pwd,subprocess
r=Path('/var/lib/samurai');o=r/'k268-unlocked-session';target=r/'k268-unlocked-session-r2/cleanup-private.json'
assert not target.exists();assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k267-work/boot-id-private.txt').read_bytes()
for n in ['7-0010','9-0010']:assert Path('/sys/bus/i2c/devices',n,'power/runtime_status').read_text().strip()=='suspended'
assert not any((p/'comm').exists() and (p/'comm').read_text().strip()=='snapshot' for p in Path('/proc').glob('[0-9]*'))
info=json.loads((o/'override-backup-private.json').read_text());extra=json.loads((o/'additional-override-private.json').read_text())
for row,digest in [(info,info['test_override_sha256']),(extra,extra['sha256'])]:
 p=Path(row['path']);assert not p.is_symlink() and hashlib.sha256(p.read_bytes()).hexdigest()==digest
for row in [info,extra]:
 p=Path(row['path'])
 if row['existed']:
  assert row is info
  p.write_bytes((o/'original-user-override-private.desktop').read_bytes());p.chmod(row['mode']);os.chown(p,row['uid'],row['gid'])
 else:p.unlink()
assert hashlib.sha256(Path('/usr/share/applications/mobi.phosh.Shell.desktop').read_bytes()).hexdigest()==info['source_sha256']
p=next(p for p in Path('/proc').glob('[0-9]*') if (p/'comm').exists() and (p/'comm').read_text().strip()=='phosh')
raw={k.decode():v.decode() for x in (p/'environ').read_bytes().split(b'\0') if b'=' in x for k,v in [x.split(b'=',1)]}
env={k:v for k,v in raw.items() if k in ['PATH','HOME','USER','LOGNAME','LANG','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS','WAYLAND_DISPLAY']};u=pwd.getpwuid(10000)
def demote():os.initgroups(u.pw_name,u.pw_gid);os.setgid(u.pw_gid);os.setuid(u.pw_uid)
saved=json.loads((r/'k268-unlocked-session-r2/settings-before-private.json').read_text())
for s in saved:
 actual=subprocess.check_output(['gsettings','get',s['schema'],s['key']],env=env,preexec_fn=demote,timeout=5).decode().strip()
 assert actual==s['test_value'],('User changed test setting; preserve it',s['key'])
for s in saved:
 subprocess.run(['gsettings','set',s['schema'],s['key'],s['before']],env=env,preexec_fn=demote,check=True,timeout=5)
 assert subprocess.check_output(['gsettings','get',s['schema'],s['key']],env=env,preexec_fn=demote,timeout=5).decode().strip()==s['before']
report=dict(stage=268,temporary_user_startup_overrides_restored=True,automatic_lock_and_idle_settings_restored=True,
 stock_shell_and_authentication_files_unchanged=True,current_session_not_restarted=True,phosh_pid=int(p.name),taint=int(Path('/proc/sys/kernel/tainted').read_text()))
target.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=30);d=json.loads(q.stdout)
(Path(__file__).parent/'session-cleanup-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d))
