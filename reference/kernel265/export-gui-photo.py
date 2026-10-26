from pathlib import Path
import hashlib,json,shlex
import host
R=Path(__file__).parent
query="from pathlib import Path;import sys;sys.stdout.buffer.write(Path('/var/lib/samurai/k265-snapshot-gui/gui-control-summary-private.json').read_bytes())"
q=host.ssh('python3 -c '+shlex.quote(query));(host.PRIVATE/'gui-capture-private.json').write_bytes(q.stdout);photos=json.loads(q.stdout)['new_jpegs']
for i,photo in enumerate(photos):
 query="from pathlib import Path;import sys;sys.stdout.buffer.write(Path("+repr(photo['path'])+").read_bytes())"
 q=host.ssh('python3 -c '+shlex.quote(query),timeout=25);assert len(q.stdout)==photo['bytes'] and hashlib.sha256(q.stdout).hexdigest()==photo['sha256']
 target=host.PRIVATE/('snapshot-photo-'+str(i)+'-private.jpeg')
 if target.exists():assert target.read_bytes()==q.stdout
 else:target.write_bytes(q.stdout)
 print(json.dumps(dict(stage=265,index=i,private_export=True,bytes=len(q.stdout),sha256_verified=True)))

