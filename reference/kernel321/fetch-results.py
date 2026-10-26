from pathlib import Path
import io,json,shlex,sys,tarfile
import host
HERE=Path(__file__).resolve().parent;run=sys.argv[1]
code='''
from pathlib import Path
import sys,tarfile
root=Path(ROOT)
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|') as tar:
 for p in [*root.glob('*-private.nv12'),*root.glob('capture-*.log')]:tar.add(p,arcname=p.name)
'''.replace('ROOT',repr('/var/lib/samurai/k321-lsc-'+run))
q=host.raw_ssh('python3 -c '+shlex.quote(code),timeout=25)
with tarfile.open(fileobj=io.BytesIO(q.stdout),mode='r:') as tar:tar.extractall(host.PRIVATE/('capture-'+run),filter='data')
d=json.loads((host.PRIVATE/('probe-'+run+'-observation.json')).read_text());assert d['state']['terminal'] and not d['worker_live']
(HERE/('native-'+run+'-validation.json')).write_text(json.dumps(d['state']['summary'],indent=2)+'\n')
print('Fetched internal pattern frames and native logs privately.')
