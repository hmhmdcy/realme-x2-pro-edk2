from pathlib import Path
import json
import host
R=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json,os,subprocess
items=[]
for p in Path('/proc').glob('[0-9]*'):
 try:
  name=(p/'comm').read_text().strip()
  if name in ['phoc','phosh','pipewire','wireplumber','iio-sensor-prox','ModemManager']:
   items.append(dict(comm=name,pid=int(p.name),start_ticks=(p/'stat').read_text().rsplit(')',1)[1].split()[19],state=(p/'stat').read_text().rsplit(')',1)[1].split()[0]))
 except OSError:pass
services={}
for name in ['greetd','samurai-ssc','iio-sensor-proxy','samurai-gnss-assist']:
 q=subprocess.run(['rc-service',name,'status'],capture_output=True,text=True,timeout=10);services[name]=dict(exit=q.returncode,text=q.stdout+q.stderr)
remote={p.name:dict(name=(p/'name').read_text().strip(),state=(p/'state').read_text().strip()) for p in Path('/sys/class/remoteproc').glob('*')}
print(json.dumps(dict(stage=273,processes=items,services=services,remoteprocs=remote)))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=45);(host.PRIVATE/'services-private.json').write_bytes(q.stdout)
d=json.loads(q.stdout);(R/'services-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
