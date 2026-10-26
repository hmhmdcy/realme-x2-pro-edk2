"""Collect only this run's early/late private samples for optical review."""
from pathlib import Path
import hashlib,json,shlex
import host
R=Path(__file__).resolve().parent
d=json.loads((host.PRIVATE/'ae-warmup-response-private.log').read_text());assert d['passed']
results=[]
for row in d['runs'][0]['photos']:
 if row['frame'] not in [36,600]:continue
 assert '/.local/state/k271-ae-warmup-r1/' in row['path']
 target=host.PRIVATE/('tele-warmup-'+str(row['frame'])+'-private.jpg');assert not target.exists()
 pieces=[]
 for offset in range(0,row['bytes'],32768):
  code="from pathlib import Path;import hashlib,sys;b=Path(%r).read_bytes();assert len(b)==%d and hashlib.sha256(b).hexdigest()==%r;sys.stdout.buffer.write(b[%d:%d])" % (row['path'],row['bytes'],row['sha256'],offset,offset+32768)
  q=host.ssh('python3 -c '+shlex.quote(code),timeout=20);assert len(q.stdout)==min(32768,row['bytes']-offset);pieces.append(q.stdout)
 raw=b''.join(pieces);assert hashlib.sha256(raw).hexdigest()==row['sha256'];target.write_bytes(raw)
 results.append(dict(frame=row['frame'],bytes=len(raw),sha256=row['sha256'],private_copy_verified=True))
(R/'ae-photo-collection-validation.json').write_text(json.dumps(dict(stage=271,photos=results,private_pixels_not_published=True),indent=2)+'\n');print(json.dumps(results,indent=2))
