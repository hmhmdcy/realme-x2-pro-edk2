"""Keep the current Phosh lock screen visible during bring-up verification."""
from pathlib import Path
import os, pwd, subprocess
pids=subprocess.check_output(['pidof','phosh'],text=True).split()
assert len(pids)==1
proc=Path('/proc')/pids[0]
assert proc.stat().st_uid==10000
env=os.environ.copy()
for entry in (proc/'environ').read_bytes().split(b'\0'):
    if b'=' not in entry: continue
    key,value=entry.split(b'=',1)
    if key in [b'HOME',b'XDG_RUNTIME_DIR',b'DBUS_SESSION_BUS_ADDRESS',b'WAYLAND_DISPLAY']:
        env[key.decode()]=value.decode()
assert env['HOME']=='/home/cy122' and env['XDG_RUNTIME_DIR']=='/run/user/10000'
user=pwd.getpwnam('cy122')
def run(args):
    subprocess.run(args,env=env,user=user.pw_uid,group=user.pw_gid,
                   extra_groups=os.getgrouplist(user.pw_name,user.pw_gid),check=True)
run(['gsettings','set','org.gnome.desktop.session','idle-delay','0'])
run(['wlr-randr','--output','DSI-1','--on'])
print('PHOSH_IDLE_BLANK_DISABLED_FOR_BRINGUP_LOCK_RETAINED')
