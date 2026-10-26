"""Transfer only this run's recorded rear JPEGs, preserving private scene data."""
from pathlib import Path
import hashlib,json,shlex
import host
R=Path(__file__).resolve().parent
data=json.loads((host.PRIVATE/'two-rear-jpeg-response-private.log').read_text());assert data['passed']
results=[]
for row in data['runs']:
 assert row['camera'] in ['wide','tele'] and '/.local/state/k270-two-rear-jpeg-r1/' in row['path']
 target=host.PRIVATE/('native-'+row['camera']+'-private.jpg');assert not target.exists();pieces=[]
 for offset in range(0,row['jpeg_bytes'],32768):
  command="from pathlib import Path;import hashlib,sys;b=Path("+repr(row['path'])+").read_bytes();assert len(b)=="+str(row['jpeg_bytes'])+" and hashlib.sha256(b).hexdigest()=="+repr(row['sha256'])+";sys.stdout.buffer.write(b["+str(offset)+":"+str(offset+32768)+"])"
  q=host.ssh('python3 -c '+shlex.quote(command),timeout=20);assert len(q.stdout)==min(32768,row['jpeg_bytes']-offset);pieces.append(q.stdout)
 raw=b''.join(pieces);assert hashlib.sha256(raw).hexdigest()==row['sha256'];target.write_bytes(raw)
 results.append(dict(camera=row['camera'],bytes=len(raw),sha256=row['sha256'],private_copy_verified=True))
(R/'two-rear-photo-collection-validation.json').write_text(json.dumps(dict(stage=270,photos=results,scene_not_published=True),indent=2)+'\n')
print(json.dumps(results,indent=2))
