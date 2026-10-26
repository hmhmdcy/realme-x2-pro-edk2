import json,re,shlex,sys
import host
run=sys.argv[1];assert re.fullmatch(r'r[1-9][0-9]*',run)
code=r'''
from pathlib import Path
import json
root=Path(ROOT);marker=root/'state.json'
if not marker.exists():
 print(json.dumps(dict(state_missing=True,root_exists=root.exists(),files=[p.name for p in root.iterdir()] if root.exists() else [])));raise SystemExit(0)
state=json.loads(marker.read_text());p=Path('/proc',str(state['pid']));live=False
try:live=str(root/'worker.py').encode() in (p/'cmdline').read_bytes() and (p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z'
except OSError:pass
print(json.dumps(dict(state=state,worker_live=live,logs={p.name:p.read_text(errors='replace') for p in root.glob('*.log')},failures={p.name:p.read_text(errors='replace') for p in root.glob('*failure*')})))
'''.replace('ROOT',repr('/var/lib/samurai/k361-request-'+run))
q=host.raw_ssh('python3 -c '+shlex.quote(code),timeout=25);facts=json.loads(q.stdout);(host.PRIVATE/('probe-'+run+'-observation.json')).write_bytes(q.stdout)
print(json.dumps({k:v for k,v in facts.items() if k!='logs'},indent=2))
