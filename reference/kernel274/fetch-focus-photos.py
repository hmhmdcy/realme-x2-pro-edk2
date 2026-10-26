"""Retain selected diagnostic photographs privately with bounded transfers and exact hashes."""
from pathlib import Path
import hashlib,json,shlex,sys
import host
attempt=int(sys.argv[1]);indices=list(map(int,sys.argv[2:]));assert attempt in [2,3]
root='/var/lib/samurai/k274-focus-position-r'+str(attempt)
q=host.ssh('cat '+shlex.quote(root+'/summary-private.json'),timeout=15);summary=json.loads(q.stdout)
assert summary['health']['passed']
photos=[]
for index in indices:
 row=next(r for r in summary['runs'] if r['index']==index);p=row['jpeg'];target=host.PRIVATE/Path(p['path']).name.replace('focus-','r'+str(attempt)+'-focus-');assert not target.exists()
 data=bytearray()
 for offset in range(0,p['bytes'],49152):
  code='from pathlib import Path;import sys;p=Path(%r);f=p.open("rb");f.seek(%d);sys.stdout.buffer.write(f.read(%d))'%(p['path'],offset,min(49152,p['bytes']-offset))
  part=host.ssh('python3 -c '+shlex.quote(code),timeout=20).stdout;assert len(part)==min(49152,p['bytes']-offset);data.extend(part)
 assert hashlib.sha256(data).hexdigest()==p['sha256'];target.write_bytes(data)
 photos.append(dict(index=index,position=row['position'],path=str(target),bytes=len(data),sha256=p['sha256']))
(host.PRIVATE/('focus-r'+str(attempt)+'-fetched-photos-private.json')).write_text(json.dumps(photos,indent=2)+'\n');print(json.dumps(photos,indent=2))
