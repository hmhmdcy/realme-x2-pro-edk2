from pathlib import Path
import json,os,pwd,subprocess
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k201-baseline/boot-id-private.txt').read_bytes()
user=pwd.getpwuid(10000)
def demote():os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(10000)
env={**os.environ,'XDG_RUNTIME_DIR':'/run/user/10000','DBUS_SESSION_BUS_ADDRESS':'unix:path=/run/user/10000/bus','HOME':user.pw_dir}
p=subprocess.run(['gsettings','get','org.gnome.system.location','enabled'],preexec_fn=demote,env=env,capture_output=True,text=True,timeout=10)
assert p.returncode==0 and p.stdout.strip() in ['true','false']
r=dict(stage=201,read_only=True,uid=10000,desktop_location_enabled=p.stdout.strip()=='true',session_bus_exists=Path('/run/user/10000/bus').exists())
(root/'k201-geoclue-install/desktop-switch.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
