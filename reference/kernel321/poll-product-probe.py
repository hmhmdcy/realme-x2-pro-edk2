import json,shlex,sys
import host
code='''
from pathlib import Path
import json
root=Path(ROOT);s=json.loads((root/'state.json').read_text())
p=Path('/proc',str(s['pid']),'stat');live=p.exists() and p.read_text().rsplit(')',1)[1].split()[0]!='Z'
print(json.dumps({'state':s,'worker_live':live,'logs':{p.name:p.read_text(errors='replace')[-4000:] for p in root.glob('*.log')},'failures':{p.name:p.read_text() for p in root.glob('*failure*')}},indent=2))
'''.replace('ROOT',repr('/var/lib/samurai/k321-product-'+sys.argv[1]))
q=host.raw_ssh('python3 -c '+shlex.quote(code),timeout=20)
(host.PRIVATE/('product-'+sys.argv[1]+'-observation.json')).write_bytes(q.stdout)
d=json.loads(q.stdout)
if '--brief' in sys.argv:print(json.dumps({k:d[k] for k in ['state','worker_live','failures']},indent=2))
else:print(q.stdout.decode())
