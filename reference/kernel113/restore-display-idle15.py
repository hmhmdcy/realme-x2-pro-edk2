"""Restore the preserved 60-second idle policy without changing the lock."""
from pathlib import Path
import json,os,pwd,subprocess
assert subprocess.check_output(['uname','-v']).startswith(b'#113 ')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k113-reboot-audio-clean-15/boot-id-private.txt').read_bytes()
saved=Path('/var/lib/samurai/k113-display-visible15/idle-delay-before.txt').read_text().strip()
assert saved=='uint32 60'
dest=Path('/var/lib/samurai/k113-display-idle-restored15')
dest.mkdir(mode=0o700)
os.umask(0o077)
pids=subprocess.check_output(['pgrep','-u','10000','-x','phosh'],text=True).split()
assert len(pids)==1
proc=Path('/proc')/pids[0]
assert proc.stat().st_uid==10000
env={'PATH':'/usr/local/bin:/usr/bin:/bin'}
for entry in (proc/'environ').read_bytes().split(b'\0'):
    if b'=' not in entry:continue
    key,value=entry.split(b'=',1)
    if key in (b'XDG_RUNTIME_DIR',b'DBUS_SESSION_BUS_ADDRESS',b'WAYLAND_DISPLAY'):env[key.decode()]=value.decode()
assert env['XDG_RUNTIME_DIR']=='/run/user/10000'
user=pwd.getpwnam('cy122')
kwargs=dict(env=env,user=user.pw_uid,group=user.pw_gid,extra_groups=os.getgrouplist(user.pw_name,user.pw_gid),timeout=12,check=True,capture_output=True)
schema='org.gnome.desktop.session';key='idle-delay'
before=subprocess.run(['gsettings','get',schema,key],**kwargs).stdout.decode().strip()
assert before=='uint32 0'
subprocess.run(['gsettings','set',schema,key,'60'],**kwargs)
after=subprocess.run(['gsettings','get',schema,key],**kwargs).stdout.decode().strip()
assert after==saved
(dest/'result.json').write_text(json.dumps(dict(before=before,after=after,original_idle_policy_restored=True,
    lock_unchanged=True,boot_checkpoint='reboot-audio-clean-15'),indent=2)+'\n')
(dest/'boot-id-private.txt').write_bytes(Path('/proc/sys/kernel/random/boot_id').read_bytes())
(dest/'taint.txt').write_bytes(Path('/proc/sys/kernel/tainted').read_bytes())
print('ORIGINAL_60_SECOND_IDLE_POLICY_RESTORED_LOCK_UNCHANGED')
