"""Preserve the session idle setting and keep this guarded boot visible."""
from pathlib import Path
import json, os, pwd, subprocess

def capture(args, **kwargs):
    return subprocess.check_output(args, timeout=12, **kwargs)

assert capture(['uname','-v']).startswith(b'#113 ')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k113-reboot-audio-clean-15/boot-id-private.txt').read_bytes()
assert Path('/sys/class/remoteproc/remoteproc0/state').read_text().strip()=='offline'
assert Path('/sys/devices/platform/sensor-power/state').read_text().strip()=='vdd=0 vddio=0'
assert Path('/var/lib/samurai/k113-display-trace15/SHA256SUMS').is_file()
dest=Path('/var/lib/samurai/k113-display-visible15')
dest.mkdir(mode=0o700)
os.umask(0o077)
pids=capture(['pgrep','-u','10000','-x','phosh']).decode().split()
assert len(pids)==1
proc=Path('/proc')/pids[0]
assert proc.stat().st_uid==10000
session_vars={}
for entry in (proc/'environ').read_bytes().split(b'\0'):
    if b'=' not in entry: continue
    key,value=entry.split(b'=',1)
    if key in (b'XDG_RUNTIME_DIR',b'DBUS_SESSION_BUS_ADDRESS',b'WAYLAND_DISPLAY'):
        session_vars[key.decode()]=value.decode()
assert session_vars['XDG_RUNTIME_DIR']=='/run/user/10000'
assert session_vars['WAYLAND_DISPLAY']=='wayland-0'
user=pwd.getpwnam('cy122')
env={'PATH':'/usr/local/bin:/usr/bin:/bin', **session_vars}
kwargs=dict(env=env,user=user.pw_uid,group=user.pw_gid,
            extra_groups=os.getgrouplist(user.pw_name,user.pw_gid))
schema='org.gnome.desktop.session'
setting='idle-delay'
before=capture(['gsettings','get',schema,setting],**kwargs)
(dest/'idle-delay-before.txt').write_bytes(before)
(dest/'dmesg-before.txt').write_bytes(capture(['dmesg']))
(dest/'taint-before.txt').write_bytes(Path('/proc/sys/kernel/tainted').read_bytes())
(dest/'boot-id-private.txt').write_bytes(Path('/proc/sys/kernel/random/boot_id').read_bytes())
(dest/'output-before.txt').write_bytes(capture(['wlr-randr'],**kwargs))
subprocess.run(['gsettings','set',schema,setting,'0'],check=True,timeout=12,**kwargs)
after=capture(['gsettings','get',schema,setting],**kwargs)
assert after.strip()==b'uint32 0'
(dest/'idle-delay-after.txt').write_bytes(after)
subprocess.run(['wlr-randr','--output','DSI-1','--on'],check=True,timeout=12,**kwargs)
(dest/'output-after.txt').write_bytes(capture(['wlr-randr'],**kwargs))
(dest/'dmesg-after.txt').write_bytes(capture(['dmesg']))
(dest/'taint-after.txt').write_bytes(Path('/proc/sys/kernel/tainted').read_bytes())
(dest/'change.json').write_text(json.dumps(dict(setting=schema+'.'+setting,
    before=before.decode().strip(),after=after.decode().strip(),
    unlock_credentials_unchanged=True,original_setting_preserved=True,
    bringup_setting_needs_restoration=True),indent=2)+'\n')
print('CURRENT_SESSION_IDLE_DELAY_SAVED_AND_DISABLED_FOR_BRINGUP; LOCK_RETAINED')
