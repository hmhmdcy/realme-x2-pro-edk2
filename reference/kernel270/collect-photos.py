"""Collect only the two JPEGs created by this recorded GUI transaction."""
from pathlib import Path
import hashlib,json,shlex
import host
R=Path(__file__).resolve().parent
code="from pathlib import Path;import json;print(json.dumps(json.loads(Path('/var/lib/samurai/k270-snapshot-gui-r1/gui-control-summary-private.json').read_text())['new_jpegs']))"
photos=json.loads(host.ssh('python3 -c '+shlex.quote(code),timeout=15).stdout)
out=[]
for row in sorted(photos,key=lambda r:r['camera']!='rear'):
 assert row['camera'] in ['front','rear']
 target=host.PRIVATE/('gui-'+row['camera']+'-private.jpg')
 if target.exists():
  payload=target.read_bytes()
 else:
  pieces=[]
  for offset in range(0,row['bytes'],32768):
   fetch="from pathlib import Path;import hashlib,sys;p=Path("+repr(row['path'])+");b=p.read_bytes();assert len(b)=="+repr(row['bytes'])+" and hashlib.sha256(b).hexdigest()=="+repr(row['sha256'])+";sys.stdout.buffer.write(b["+str(offset)+":"+str(offset+32768)+"])"
   q=host.ssh('python3 -c '+shlex.quote(fetch),timeout=20)
   assert len(q.stdout)==min(32768,row['bytes']-offset)
   pieces.append(q.stdout)
  payload=b''.join(pieces)
  assert len(payload)==row['bytes'] and hashlib.sha256(payload).hexdigest()==row['sha256']
  target.write_bytes(payload)
 assert len(payload)==row['bytes'] and hashlib.sha256(payload).hexdigest()==row['sha256']
 out.append(dict(camera=row['camera'],bytes=row['bytes'],sha256=row['sha256'],own_recorded_capture_only=True,private_host_copy_verified=True))
(R/'gui-photo-collection-validation.json').write_text(json.dumps(dict(stage=270,photos=out,scene_not_published=True),indent=2)+'\n')
print(json.dumps(out,indent=2))
