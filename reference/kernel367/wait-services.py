"""Wait for normal desktop readiness before creating a capture transaction."""
from pathlib import Path
import json,shlex
import host
HERE=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json,subprocess,time
deadline=time.monotonic()+45
while True:
 counts={n:0 for n in ['pipewire','wireplumber','phoc','phosh']}
 for p in Path('/proc').glob('[0-9]*'):
  try:
   name=(p/'comm').read_text().strip()
   if name in counts and (p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z':counts[name]+=1
  except OSError:pass
 state=Path('/run/samurai-ssc/state.json');ssc=json.loads(state.read_text()) if state.exists() else {}
 ready=all(v==1 for v in counts.values()) and ssc.get('started') is True
 if ready or time.monotonic()>=deadline:break
 time.sleep(.5)
services={}
for n in ['samurai-ssc','iio-sensor-proxy','greetd']:
 q=subprocess.run(['rc-service',n,'status'],capture_output=True,text=True,timeout=10);services[n]=dict(exit=q.returncode,text=(q.stdout+q.stderr).strip())
print(json.dumps(dict(stage=367,ready=ready,process_counts=counts,ssc_started=ssc.get('started'),services=services,uptime=float(Path('/proc/uptime').read_text().split()[0]))))
'''
q=host.ssh('python3 -c '+shlex.quote(code),timeout=60);d=json.loads(q.stdout);(HERE/'services-ready-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
