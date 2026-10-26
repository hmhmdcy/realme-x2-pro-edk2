"""Save process boot timestamps without exposing PID/session identity."""
from pathlib import Path
import json, os, subprocess, time
os.umask(0o077)
assert os.uname().version.startswith('#156 ')
out=Path('/var/lib/samurai/k156-boot-timing')
assert not out.exists();out.mkdir(mode=0o700)
uptime=float(Path('/proc/uptime').read_text().split()[0])
epoch=time.time()-uptime
ticks=os.sysconf('SC_CLK_TCK')
processes={}
for name in ['dbus-daemon','greetd','phoc','phosh','NetworkManager','chronyd']:
    pids=subprocess.run(['pgrep','-x',name],capture_output=True,text=True).stdout.split()
    starts=[]
    for pid in pids:
        stat=Path('/proc')/pid/'stat'
        if stat.exists():starts.append(int(stat.read_text().rsplit(')',1)[1].split()[19])/ticks)
    processes[name]=sorted(starts)
services={}
for name in ['dbus','greetd','samurai-radio','networkmanager','chronyd']:
    p=Path('/run/openrc/started')/name
    services[name]=p.lstat().st_mtime-epoch if p.is_symlink() else None
tree=Path('/run/openrc/deptree').read_text()
(out/'deptree-private.txt').write_text(tree)
result=dict(stage=156,uptime=uptime,process_start_uptime=processes,
    service_started_uptime_approximate=services,
    service_times_from_lstat=True,service_times_subject_to_wallclock_adjustment=True,
    phosh_before_radio_complete=bool(processes['phosh'] and services['samurai-radio'] is not None
        and min(processes['phosh'])<services['samurai-radio']))
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result),flush=True)
