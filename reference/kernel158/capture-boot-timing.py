from pathlib import Path
import json,os,subprocess
os.umask(0o077)
assert os.uname().version.startswith('#158 ')
out=Path('/var/lib/samurai/k158-boot-timing');assert not out.exists();out.mkdir(mode=0o700)
ticks=os.sysconf('SC_CLK_TCK');processes={}
for name in ['dbus-daemon','greetd','phoc','phosh','NetworkManager','chronyd']:
    ids=subprocess.run(['pgrep','-x',name],capture_output=True,text=True).stdout.split();starts=[]
    for pid in ids:
        p=Path('/proc')/pid/'stat'
        if p.exists():starts.append(int(p.read_text().rsplit(')',1)[1].split()[19])/ticks)
    processes[name]=sorted(starts)
result=dict(stage=158,uptime=float(Path('/proc/uptime').read_text().split()[0]),
    process_start_uptime=processes,process_timestamps_from_monotonic_proc_stat=True,
    physical_lockscreen_timing_validation_pending=True)
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
