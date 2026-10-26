import io, json, shlex, sys, tarfile
import host

run = sys.argv[1]
d = json.loads((host.PRIVATE / ('probe-' + run + '-observation.json')).read_text())
assert d['state']['terminal'] and not d['worker_live']
code = '''
from pathlib import Path
import sys,tarfile
root=Path(ROOT)
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|') as tar:
 for p in root.glob('*-private.nv12'):tar.add(p,arcname=p.name)
'''.replace('ROOT', repr('/var/lib/samurai/k330-cct-' + run))
q = host.raw_ssh('python3 -c ' + shlex.quote(code), timeout=25)
with tarfile.open(fileobj=io.BytesIO(q.stdout), mode='r:') as tar:
    tar.extractall(host.PRIVATE / ('images-' + run), filter='data')
print('Fetched paired internal-pattern NV12 privately.')
