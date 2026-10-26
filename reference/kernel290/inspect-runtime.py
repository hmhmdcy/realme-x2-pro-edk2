"""Revalidate actual boot, terminated prior workers and idle camera resources."""
from pathlib import Path
import json
import host

ROOT=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json,os,re,subprocess
assert os.uname().version.startswith('#288 ')
workers=[]
for name in ['k289-dmi-r1','k289-dmi-r2','k289-baseline-r1','k289-dmi-r3','k289-dmi-r4','k289-dmi-r5','k289-gamma-r1','k289-cst-r1']:
 s=json.loads(Path('/var/lib/samurai',name,'state-private.json').read_text());exists=Path('/proc',str(s['pid'])).exists()
 assert s['terminal'] and not exists;workers.append(dict(name=name,terminal=True,process_gone=True))
sensors={}
for driver in ['s5kgw1','s5k3m5','imx319','imx471','lc898219xi']:
 for p in Path('/sys/bus/i2c/drivers',driver).glob('*'):
  if p.is_symlink() and re.fullmatch(r'\d+-[0-9a-f]{4}',p.name):sensors[driver]=(p/'power/runtime_status').read_text().strip()
assert len(sensors)==5 and all(v=='suspended' for v in sensors.values())
d=subprocess.check_output(['dmesg']);faults={k:d.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu_fault=b'gpu fault:',dsp_fatal=b'fatal error received').items()}
assert not any(faults.values()) and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
print(json.dumps(dict(stage=290,kernel_build=288,release=os.uname().release,previous_workers=workers,sensor_pm=sensors,faults=faults,taint=0)))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=20)
r=json.loads(q.stdout);(ROOT/'runtime-preflight-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
