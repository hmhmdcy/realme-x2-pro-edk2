from pathlib import Path
import io,json,shlex,tarfile,sys
import host
HERE=Path(__file__).resolve().parent
run=sys.argv[1] if len(sys.argv)>1 else 'r1'
code="""
from pathlib import Path
import io,sys,tarfile
root=Path(ROOT)
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|') as tar:
 for p in [root/'capture-pattern.log',*sorted(root.glob('pattern-private-phase*.nv12'))]:tar.add(p,arcname=p.name)
""".replace('ROOT',repr('/var/lib/samurai/k348-gamma-'+run))
q=host.raw_ssh('python3 -c '+shlex.quote(code),timeout=20)
with tarfile.open(fileobj=io.BytesIO(q.stdout),mode='r:') as tar:tar.extractall(host.PRIVATE/('pattern-'+run),filter='data')
d=json.loads((host.PRIVATE/('probe-'+run+'-observation.json')).read_text())
(HERE/('pattern-'+run+'-capture-validation.json')).write_text(json.dumps(d['state']['summary'],indent=2)+'\n')
print((host.PRIVATE/('pattern-'+run)/'capture-pattern.log').read_text()[-1200:])
