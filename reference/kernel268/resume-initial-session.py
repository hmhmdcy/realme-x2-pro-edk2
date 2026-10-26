"""Resume the configured initial login after observing greetd's completed-login marker."""
from pathlib import Path
import json
import host

code=r'''
from pathlib import Path
import hashlib,json,os,pwd,shutil,subprocess,time,traceback
os.umask(0o077);r=Path('/var/lib/samurai');o=r/'k268-unlocked-session';phase=o/'resume-state-private.json'
assert not phase.exists();state=dict(stage=268,state='observed_greeter_after_known_restart',terminal=False)
def save():phase.write_text(json.dumps(state,indent=2)+'\n')
save()
try:
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k267-work/boot-id-private.txt').read_bytes()
 assert json.loads((o/'state-private.json').read_text())['terminal']
 marker=Path('/run/greetd.run');assert marker.is_file() and not marker.is_symlink() and marker.stat().st_size==0
 config=Path('/etc/greetd/samurai-phosh.toml').read_text();assert '[initial_session]' in config and 'samurai-phosh-session' in config
 u=pwd.getpwuid(10000);source=Path(u.pw_dir,'.local/share/applications/mobi.phosh.Shell.desktop')
 assert 'Exec=/usr/libexec/phosh --unlocked\n' in source.read_text()
 override=Path(u.pw_dir,'.config/autostart/mobi.phosh.Shell.desktop');assert not override.exists()
 override.parent.mkdir(parents=True,exist_ok=True);override.write_bytes(source.read_bytes());override.chmod(0o644);os.chown(override,u.pw_uid,u.pw_gid)
 (o/'additional-override-private.json').write_text(json.dumps(dict(path=str(override),existed=False,sha256=hashlib.sha256(override.read_bytes()).hexdigest()))+'\n')
 q=subprocess.run(['rc-service','greetd','stop'],capture_output=True,timeout=35)
 (o/'resume-stop-greetd-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0
 assert marker.is_file() and marker.stat().st_size==0;shutil.copy2(marker,o/'initial-login-runfile-private.before');marker.unlink()
 state.update(state='restarting_configured_initial_login');save()
 q=subprocess.run(['rc-service','greetd','start'],capture_output=True,timeout=35)
 (o/'resume-start-greetd-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0
 deadline=time.monotonic()+35;proc=None
 while time.monotonic()<deadline:
  for p in Path('/proc').glob('[0-9]*'):
   try:
    if (p/'comm').read_text().strip()=='phosh' and b'--unlocked' in (p/'cmdline').read_bytes():proc=p;break
   except OSError:pass
  if proc:break
  time.sleep(.3)
 assert proc,'Inspect this recorded initial-session transition before further action'
 state.update(state='terminal',terminal=True,exit_code=0);save()
 report=dict(stage=268,supported_unlocked_phosh_session_running=True,phosh_pid=int(proc.name),
 phosh_start_ticks=(proc/'stat').read_text().rsplit(')',1)[1].split()[19],
 configured_initial_login_resumed=True,known_zero_length_greetd_runtime_marker_preserved=True,
 stock_shell_session_and_authentication_files_unchanged=True,user_override_cleanup_pending=True)
 (o/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
except BaseException:
 (o/'resume-failure-private.txt').write_text(traceback.format_exc());state.update(state='failed',terminal=True,exit_code=1);save();raise
'''
q=host.ssh('python3 -',input=code.encode(),timeout=100,check=False)
(host.PRIVATE/'resume-initial-session-response-private.log').write_bytes(q.stdout+q.stderr)
assert q.returncode==0 and q.stdout,'Inspect the recorded initial-session state before any repeat'
d=json.loads(q.stdout);(Path(__file__).parent/'unlocked-session-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d))
