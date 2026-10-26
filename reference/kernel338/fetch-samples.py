import io,json,shlex,sys,tarfile
import host
run=sys.argv[1];data=json.loads((host.PRIVATE/('probe-'+run+'-observation.json')).read_text());assert data['state']['terminal'] and not data['worker_live']
code='''
from pathlib import Path
import sys,tarfile
root=Path(ROOT)
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|') as tar:
 for path in root.glob('sample-*-private.*'):tar.add(path,arcname=path.name)
'''.replace('ROOT',repr('/var/lib/samurai/k338-grid-'+run))
q=host.raw_ssh('python3 -c '+shlex.quote(code),timeout=25)
with tarfile.open(fileobj=io.BytesIO(q.stdout),mode='r:') as tar:tar.extractall(host.PRIVATE/('samples-'+run),filter='data')
print('Fetched four private image/statistics pairs.')
