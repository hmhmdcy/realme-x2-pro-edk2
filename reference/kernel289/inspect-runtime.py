"""Read actual kernel, prior worker identities and idle camera state before diagnostics."""
from pathlib import Path
import json
import host

code = r'''
from pathlib import Path
import json,os,re,subprocess
assert os.uname().version.startswith('#288 ')
sensors={}
for driver in ['s5kgw1','s5k3m5','imx319','imx471','lc898219xi']:
 for p in Path('/sys/bus/i2c/drivers',driver).glob('*'):
  if p.is_symlink() and re.fullmatch(r'\d+-[0-9a-f]{4}',p.name):
   sensors[driver]=(p/'power/runtime_status').read_text().strip()
workers=[]
for name in ['k288-tpg-r1','k288-tpg-r2','k288-tpg-r3','k288-rdi-control-r1','k288-four-camera-regression-r1']:
 p=Path('/var/lib/samurai',name,'state-private.json');s=json.loads(p.read_text());pid=s['pid'];proc=Path('/proc',str(pid))
 workers.append(dict(name=name,terminal=s['terminal'],pid_exists=proc.exists(),exit_code=s.get('exit_code')))
cmdline=Path('/proc/cmdline').read_text()
d=subprocess.check_output(['dmesg'])
report=dict(stage=289,kernel_build=288,release=os.uname().release,sensor_pm=sensors,prior_workers=workers,
 taint=int(Path('/proc/sys/kernel/tainted').read_text()),
 bringup_retention_flags=[x for x in cmdline.split() if x in ['clk_ignore_unused','pd_ignore_unused','regulator_ignore_unused']],
 faults={k:d.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu_fault=b'gpu fault:',dsp_fatal=b'fatal error received').items()})
assert len(sensors)==5 and all(v=='suspended' for v in sensors.values())
assert all(w['terminal'] and not w['pid_exists'] for w in workers)
assert report['taint']==0 and not any(report['faults'].values())
print(json.dumps(report))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=20)
report=json.loads(q.stdout)
(Path(__file__).resolve().parent/'runtime-preflight-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
