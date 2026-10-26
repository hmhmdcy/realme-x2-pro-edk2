from pathlib import Path
import json, shlex, sys
import host

HERE = Path(__file__).resolve().parent
run = sys.argv[1]
code = '''
from pathlib import Path
import json
root=Path(ROOT);s=json.loads((root/'state.json').read_text());p=Path('/proc',str(s['pid']),'stat')
live=p.exists() and p.read_text().rsplit(')',1)[1].split()[0]!='Z'
print(json.dumps(dict(state=s,worker_live=live,logs={p.name:p.read_text(errors='replace') for p in root.glob('*.log')},failures={p.name:p.read_text() for p in root.glob('*failure*')})))
'''.replace('ROOT', repr('/var/lib/samurai/k330-cct-' + run))
q = host.raw_ssh('python3 -c ' + shlex.quote(code), timeout=25)
(host.PRIVATE / ('probe-' + run + '-observation.json')).write_bytes(q.stdout)
d = json.loads(q.stdout)
if d['state']['terminal']:
    assert not d['worker_live']
    (HERE / ('probe-' + run + '-validation.json')).write_text(json.dumps(d['state']['summary'], indent=2) + '\n')
print(json.dumps({k: d[k] for k in ['state', 'worker_live', 'failures']}, indent=2))
