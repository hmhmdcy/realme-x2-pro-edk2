"""Read one submitted run and its actual process handle; never relaunch."""
from pathlib import Path
import json,shlex,sys
import host
kind,run=sys.argv[1:3]
code=r'''
from pathlib import Path
import json
root=Path(ROOT);state=json.loads((root/'state.json').read_text())
def live(pid):
    p=Path('/proc',str(pid),'stat')
    return p.exists() and p.read_text().rsplit(')',1)[1].split()[0]!='Z'
result={'state':state,'worker_live':live(state['pid']),'child_live':live(state.get('child_pid',-1))}
for p in root.glob('*.log'):result[p.name]=p.read_text(errors='replace')[-2200:]
for p in root.glob('*failure*'):result[p.name]=p.read_text(errors='replace')[-2200:]
print(json.dumps(result,indent=2))
'''.replace('ROOT',repr('/var/lib/samurai/k312-'+kind+'-'+run))
q=host.raw_ssh('python3 -c '+shlex.quote(code),timeout=20)
(host.PRIVATE/(kind+'-'+run+'-observation.json')).write_bytes(q.stdout)
print(q.stdout.decode())
