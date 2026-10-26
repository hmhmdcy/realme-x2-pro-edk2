from pathlib import Path
import json,shlex
import host
code=r'''
from pathlib import Path
import json,subprocess
root=Path('/run/samurai-ssc');data={}
for name in ['state.json','failure-private.txt','transitions-private.log','hexagonrpcd-private.log']:
 p=root/name
 if p.exists():data[name]=p.read_text(errors='replace')[-16000:]
data['files']=[p.name for p in root.iterdir()] if root.exists() else []
data['remoteprocs']={ (p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('*') }
data['sensor_power']=Path('/sys/devices/platform/sensor-power/state').read_text().strip()
data['rc_tail']=Path('/var/log/rc.log').read_text(errors='replace')[-16000:]
print(json.dumps(data))
'''
q=host.ssh('python3 -c '+shlex.quote(code),timeout=20);d=json.loads(q.stdout);(host.PRIVATE/'ssc-observation-private.json').write_bytes(q.stdout)
state=json.loads(d.get('state.json','{}'))
print(json.dumps(dict(remoteprocs=d['remoteprocs'],power=d['sensor_power'],state={k:v for k,v in state.items() if k in ['phase','status','state','error','failure']},files=d['files'],daemon_error_lines=[l for l in d.get('hexagonrpcd-private.log','').splitlines() if any(w in l.lower() for w in ['error','failed','denied','invalid'])][-12:],rc_errors=[l for l in d['rc_tail'].splitlines() if any(w in l.lower() for w in ['ssc','sensor','failed','error','greetd'])][-24:]),indent=2))
