"""Inspect the existing worker; never relaunch on an observation timeout."""
import shlex
import sys
import host
code=r'''
from pathlib import Path
import json
root=Path(RUN_ROOT)
p=root/'state.json'
state=json.loads(p.read_text()) if p.exists() else {}
print(json.dumps(state,indent=2))
pid=state.get('pid')
if pid:
    process=Path('/proc',str(pid),'stat')
    print('worker_live=',process.exists() and process.read_text().rsplit(')',1)[1].split()[0]!='Z')
for name in ['failure.txt','restore-failure.txt','worker.log','capture.log','unload-deployed.log']:
    f=root/name
    if f.exists():print(name+'\n'+f.read_text(errors='replace')[-4500:])
'''
code=code.replace('RUN_ROOT',repr('/var/lib/samurai/k307-rgb-r2' if len(sys.argv)>1 and sys.argv[1]=='tele' else '/var/lib/samurai/k307-rgb-r1'))
q=host.raw_ssh('python3 -c '+shlex.quote(code),timeout=20)
(host.PRIVATE/'probe-latest.txt').write_bytes(q.stdout)
print(q.stdout.decode())
