"""Read default service progress before starting camera work."""
from pathlib import Path
import json
import host
HERE=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json,subprocess
p=Path('/run/samurai-ssc/state.json')
commands={}
for args in [['rc-status','--all'],['rc-status','--runlevel']]:
 q=subprocess.run(args,capture_output=True,text=True);commands[' '.join(args)]=dict(exit=q.returncode,text=q.stdout+q.stderr)
print(json.dumps(dict(uptime=float(Path('/proc/uptime').read_text().split()[0]),ssc_state=json.loads(p.read_text()) if p.exists() else None,
 services={n:subprocess.run(['rc-service',n,'status'],capture_output=True).returncode==0 for n in ['greetd','samurai-ssc','iio-sensor-proxy']},commands=commands)))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=20)
(host.PRIVATE/'startup-readiness-private.json').write_bytes(q.stdout)
report=json.loads(q.stdout)
if report['ssc_state']:
 report['ssc_state'].pop('boot_id',None)
(HERE/'startup-readiness-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
