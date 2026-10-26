"""Observe the existing phone worker and bounded recent log output."""
import shlex,sys
import host
version=sys.argv[1] if len(sys.argv)>1 else 'r1'
code=r'''
from pathlib import Path
import json
root=Path(RUN_ROOT)
state=json.loads((root/'state.json').read_text())
print(json.dumps(state,indent=2))
p=Path('/proc',str(state['pid']),'stat')
print('worker_live=',p.exists() and p.read_text().rsplit(')',1)[1].split()[0]!='Z')
for name in ['failure.txt','restore-failure.txt','worker.log','capture.log']:
    p=root/name
    if p.exists():print(name+'\n'+p.read_text(errors='replace')[-7000:])
'''
code=code.replace('RUN_ROOT',repr('/var/lib/samurai/k308-awb-'+version))
q=host.raw_ssh('python3 -c '+shlex.quote(code),timeout=20)
(host.PRIVATE/('observation-'+version+'.txt')).write_bytes(q.stdout)
print(q.stdout.decode())
