from pathlib import Path
import host,json

code=r'''
from pathlib import Path
import json,subprocess
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k219-runtime/boot-id-private.txt').read_bytes()
out=root/'k219-runtime'
states={}
for p in [Path('/run/samurai-ssc/state.json'),root/'gnss-assist/watch-state.json']:
    if p.exists():states[str(p)]=json.loads(p.read_text())
service={}
for name in ['samurai-ssc','radio','samurai-gnss-assist']:
    p=subprocess.run(['rc-service',name,'status'],capture_output=True,text=True,timeout=10);service[name]=dict(exit=p.returncode,text=p.stdout+p.stderr)
logs=subprocess.run(['logread','-l','120'],capture_output=True,text=True,timeout=10)
(out/'readiness-state-private.json').write_text(json.dumps(states,indent=2)+'\n');(out/'readiness-services-private.json').write_text(json.dumps(service,indent=2)+'\n');(out/'readiness-log-private.txt').write_text(logs.stdout+logs.stderr)
report=dict(uptime=float(Path('/proc/uptime').read_text().split()[0]),remoteprocs={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')},ssc_started=states.get('/run/samurai-ssc/state.json',{}).get('started'),service_status={k:v['exit'] for k,v in service.items()},taint=int(Path('/proc/sys/kernel/tainted').read_text()))
print(json.dumps(report))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=45);(host.PRIVATE/'readiness-host-private.json').write_bytes(p.stdout);print(p.stdout.decode().strip())
