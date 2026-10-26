"""Resolve the first new-boot validation assertion from actual current state."""
from pathlib import Path
import ast,json
import host

ROOT=Path(__file__).resolve().parent
failure=host.PRIVATE/'ssh-last-failure-private.log'
saved=host.PRIVATE/'postboot-runtime-first-error-private.txt'
assert failure.exists() and not saved.exists();saved.write_bytes(failure.read_bytes())
tree=ast.parse((ROOT/'check-new-runtime.py').read_text())
code=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='code' for t in n.targets))
print('First assertion line 22: '+code.splitlines()[21])
diagnostic=r'''
from pathlib import Path
import json,re,subprocess
sensors={}
for driver in ['s5kgw1','s5k3m5','imx319','imx471','lc898219xi']:
 for p in Path('/sys/bus/i2c/drivers',driver).glob('*'):
  if p.is_symlink() and re.fullmatch(r'\d+-[0-9a-f]{4}',p.name):sensors[driver]=(p/'power/runtime_status').read_text().strip()
d=subprocess.check_output(['dmesg']);print(json.dumps(dict(sensors=sensors,taint=Path('/proc/sys/kernel/tainted').read_text().strip(),
 faults={k:d.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu_fault=b'gpu fault:',dsp_fatal=b'fatal error received').items()},
 services={n:subprocess.run(['rc-service',n,'status'],capture_output=True).returncode==0 for n in ['greetd','samurai-ssc','iio-sensor-proxy']})))
'''
q=host.ssh('python3 -',input=diagnostic.encode(),timeout=25)
r=json.loads(q.stdout);(ROOT/'postboot-first-check-followup-validation.json').write_text(json.dumps(dict(stage=290,first_assertion=code.splitlines()[21],current=r),indent=2)+'\n');print(json.dumps(r,indent=2))
