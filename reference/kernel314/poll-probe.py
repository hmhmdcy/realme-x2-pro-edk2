import json,shlex,sys
import host
code='''
from pathlib import Path
import json
root=Path(ROOT);s=json.loads((root/'state.json').read_text())
p=Path('/proc',str(s['pid']),'stat');live=p.exists() and p.read_text().rsplit(')',1)[1].split()[0]!='Z'
print(json.dumps({'state':s,'worker_live':live,'logs':{p.name:p.read_text(errors='replace')[-2500:] for p in root.glob('*.log')},'failures':{p.name:p.read_text() for p in root.glob('*failure*')}},indent=2))
'''.replace('ROOT',repr('/var/lib/samurai/k314-dual-'+sys.argv[1]))
q=host.raw_ssh('python3 -c '+shlex.quote(code),timeout=20)
(host.PRIVATE/('dual-'+sys.argv[1]+'-observation.json')).write_bytes(q.stdout)
print(q.stdout.decode())
