from pathlib import Path
import json,shlex
import host
HERE=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json,subprocess
services={}
for name in ['samurai-ssc','iio-sensor-proxy','greetd']:
 q=subprocess.run(['rc-service',name,'status'],capture_output=True,text=True,timeout=10);services[name]=dict(exit=q.returncode,text=(q.stdout+q.stderr).strip())
counts={n:0 for n in ['pipewire','wireplumber','phoc','phosh']}
for p in Path('/proc').glob('[0-9]*'):
 try:
  name=(p/'comm').read_text().strip()
  if name in counts and (p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z':counts[name]+=1
 except OSError:pass
state=Path('/run/samurai-ssc/state.json');ssc=json.loads(state.read_text()) if state.exists() else {}
print(json.dumps(dict(stage=372,uptime=float(Path('/proc/uptime').read_text().split()[0]),services=services,process_counts=counts,
 ssc_started=ssc.get('started',False),ssc_attempted=ssc.get('attempted',False),ssc_failure=ssc.get('readiness_failure'),
 taint=int(Path('/proc/sys/kernel/tainted').read_text()),remoteprocs={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('*')},
 camera_pm={n:Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip() for n in ['acb3000.camss','ac4a000.cci','ac4b000.cci']})))
'''
q=host.ssh('python3 -c '+shlex.quote(code),timeout=25);d=json.loads(q.stdout);d['healthy']=all(x['exit']==0 for x in d['services'].values()) and all(v==1 for v in d['process_counts'].values()) and d['taint']==0
(HERE/'current-health-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
