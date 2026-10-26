from pathlib import Path
import json,os,pwd,subprocess
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k202r2-runtime/boot-id-private.txt').read_bytes()
processes=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  if (p/'comm').read_text().strip()=='phosh' and (p/'status').read_text().split('Uid:',1)[1].split()[0]=='10000':processes.append(p)
 except OSError:pass
assert len(processes)==1
entries=dict(part.split(b'=',1) for part in (processes[0]/'environ').read_bytes().split(b'\0') if b'=' in part)
keys=['DBUS_SESSION_BUS_ADDRESS','XDG_RUNTIME_DIR','GSETTINGS_BACKEND','DCONF_PROFILE','XDG_CONFIG_HOME','XDG_DATA_DIRS']
env={key:entries[key.encode()].decode() for key in keys if key.encode() in entries};assert 'DBUS_SESSION_BUS_ADDRESS' in env and 'XDG_RUNTIME_DIR' in env
(root/'k202r2-runtime/desktop-env-private.json').write_text(json.dumps(env))
user=pwd.getpwuid(10000)
def demote():os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(10000)
p=subprocess.run(['gsettings','get','org.gnome.system.location','enabled'],preexec_fn=demote,env={**os.environ,**env,'HOME':user.pw_dir},capture_output=True,text=True,timeout=10)
assert p.returncode==0 and p.stdout.strip() in ['true','false']
report=dict(stage=202,actual_phosh_session_environment_used=True,uid=10000,desktop_location_enabled=p.stdout.strip()=='true',settings_backend=env.get('GSETTINGS_BACKEND','default'),bus_address_not_assumed=True)
(root/'k202r2-runtime/actual-desktop-switch.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
