from pathlib import Path
import hashlib,json,shlex
import host
R=Path(__file__).resolve().parent
d=json.loads((host.PRIVATE/'main-ae-response-private.log').read_text());assert d['passed']
photos=[]
for row in d['runs'][0]['photos']:
 if row['frame'] not in [36,600]:continue
 assert '/.local/state/k273-main-ae-r1/' in row['path']
 target=host.PRIVATE/('main-ae-'+str(row['frame'])+'-private.jpg');assert not target.exists()
 q=host.ssh('cat '+shlex.quote(row['path']),timeout=20)
 assert len(q.stdout)==row['bytes'] and hashlib.sha256(q.stdout).hexdigest()==row['sha256'];target.write_bytes(q.stdout)
 photos.append(dict(frame=row['frame'],bytes=row['bytes'],sha256=row['sha256'],private_copy_verified=True))
(R/'main-photo-collection-validation.json').write_text(json.dumps(dict(stage=273,photos=photos,private_pixels_not_published=True),indent=2)+'\n');print(json.dumps(photos))
