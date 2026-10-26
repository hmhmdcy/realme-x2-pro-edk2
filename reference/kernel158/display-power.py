"""Use the running Phosh session's DisplayConfig power interface."""
from pathlib import Path
import os, subprocess, sys
pids = subprocess.check_output(['pgrep', '-u', '10000', '-x', 'phosh'], text=True).split()
assert len(pids) == 1
session = dict(x.split('=',1) for x in (Path('/proc')/pids[0]/'environ').read_text().split('\0') if '=' in x)
env = os.environ.copy()
for key in ['DBUS_SESSION_BUS_ADDRESS','XDG_RUNTIME_DIR','WAYLAND_DISPLAY']:
    env[key] = session[key]
os.setgroups([])
os.setgid(10000)
os.setuid(10000)
prefix=['gdbus','call','--session','--dest','org.gnome.Mutter.DisplayConfig',
    '--object-path','/org/gnome/Mutter/DisplayConfig']
if sys.argv[1] == 'get':
    args=prefix+['--method','org.freedesktop.DBus.Properties.Get',
        'org.gnome.Mutter.DisplayConfig','PowerSaveMode']
else:
    assert sys.argv[1] in ['on','off']
    args=prefix+['--method','org.freedesktop.DBus.Properties.Set',
        'org.gnome.Mutter.DisplayConfig','PowerSaveMode',
        '<int32 '+('0' if sys.argv[1]=='on' else '3')+'>']
subprocess.run(args,env=env,check=True,timeout=10)
