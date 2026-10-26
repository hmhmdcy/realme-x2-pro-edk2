"""Use Phosh's supported unlocked-start option for a bounded GUI validation session."""
from pathlib import Path
import json
import host

code=r'''
from pathlib import Path
import hashlib,json,os,pwd,subprocess,time,traceback
os.umask(0o077);r=Path('/var/lib/samurai');o=r/'k268-unlocked-session';o.mkdir(mode=0o700)
state=dict(stage=268,state='starting',terminal=False,pid=os.getpid())
def save():
 p=o/'state-next-private.json';p.write_text(json.dumps(state,indent=2)+'\n');p.replace(o/'state-private.json')
save();changed=False
try:
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k267-work/boot-id-private.txt').read_bytes()
 assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
 for name in ['7-0010','9-0010']:assert Path('/sys/bus/i2c/devices',name,'power/runtime_status').read_text().strip()=='suspended'
 found=[]
 for p in Path('/proc').glob('[0-9]*'):
  try:
   if (p/'comm').read_text().strip()=='phosh':found.append(p)
   assert (p/'comm').read_text().strip()!='snapshot'
  except OSError:pass
 assert len(found)==1;old_pid=int(found[0].name)
 u=pwd.getpwuid(10000);source=Path('/usr/share/applications/mobi.phosh.Shell.desktop')
 text=source.read_text();needle='Exec=/usr/libexec/phosh\n';assert text.count(needle)==1
 override=Path(u.pw_dir,'.local/share/applications/mobi.phosh.Shell.desktop')
 assert not override.is_symlink();before=override.read_bytes() if override.exists() else None
 info=dict(path=str(override),existed=before is not None,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
 if before is not None:
  info.update(mode=override.stat().st_mode&0o777,uid=override.stat().st_uid,gid=override.stat().st_gid)
  (o/'original-user-override-private.desktop').write_bytes(before)
 new=text.replace(needle,'Exec=/usr/libexec/phosh --unlocked\n');info['test_override_sha256']=hashlib.sha256(new.encode()).hexdigest()
 (o/'override-backup-private.json').write_text(json.dumps(info,indent=2)+'\n')
 override.parent.mkdir(parents=True,exist_ok=True);override.write_text(new);override.chmod(0o644);os.chown(override,u.pw_uid,u.pw_gid);changed=True
 state.update(state='restarting_display_session',old_phosh_pid=old_pid);save()
 for operation in ['stop','start']:
  q=subprocess.run(['rc-service','greetd',operation],capture_output=True,timeout=35)
  (o/(operation+'-greetd-private.log')).write_bytes(q.stdout+q.stderr);assert q.returncode==0
 deadline=time.monotonic()+35;newproc=None
 while time.monotonic()<deadline:
  for p in Path('/proc').glob('[0-9]*'):
   try:
    if int(p.name)!=old_pid and (p/'comm').read_text().strip()=='phosh' and b'--unlocked' in (p/'cmdline').read_bytes():newproc=p;break
   except OSError:pass
  if newproc:break
  time.sleep(.3)
 assert newproc,'Inspect session logs; do not repeat the restart'
 assert hashlib.sha256(source.read_bytes()).hexdigest()==info['source_sha256']
 report=dict(stage=268,supported_phosh_unlocked_start_verified=True,stock_shell_and_session_files_unchanged=True,
  temporary_user_override_only=True,phosh_pid=int(newproc.name),
  phosh_start_ticks=(newproc/'stat').read_text().rsplit(')',1)[1].split()[19],
  current_kernel_boot_preserved=True,startup_override_restore_pending=True)
 (o/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
 state.update(state='terminal',terminal=True,exit_code=0);save();print(json.dumps(report))
except BaseException:
 (o/'failure-private.txt').write_text(traceback.format_exc());state.update(state='failed',terminal=True,exit_code=1);save();raise
'''
q=host.ssh('python3 -',input=code.encode(),timeout=100,check=False)
(host.PRIVATE/'unlocked-session-response-private.log').write_bytes(q.stdout+q.stderr)
assert q.returncode==0 and q.stdout,'Inspect the existing session transition before retrying'
d=json.loads(q.stdout);(Path(__file__).parent/'unlocked-session-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d))
