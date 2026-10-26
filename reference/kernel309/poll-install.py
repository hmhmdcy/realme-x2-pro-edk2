"""Inspect the submitted module install without resending a transaction."""
import shlex
import host
code=r'''
from pathlib import Path
import json
root=Path('/var/lib/samurai/k309-module-install-r1')
state=json.loads((root/'state.json').read_text());print(json.dumps(state,indent=2))
p=Path('/proc',str(state['pid']),'stat')
print('worker_live=',p.exists() and p.read_text().rsplit(')',1)[1].split()[0]!='Z')
for name in ['failure.txt','rollback-failure.txt','restart-failure.txt','worker.log']:
    p=root/name
    if p.exists():print(name+'\n'+p.read_text(errors='replace')[-3000:])
'''
q=host.raw_ssh('python3 -c '+shlex.quote(code),timeout=20)
(host.PRIVATE/'install-observation.txt').write_bytes(q.stdout)
print(q.stdout.decode())
