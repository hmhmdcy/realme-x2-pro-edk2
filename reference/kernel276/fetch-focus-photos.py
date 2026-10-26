from pathlib import Path
import hashlib,json,shlex
import host
R=Path(__file__).resolve().parent;P=host.PRIVATE
q=host.ssh('cat /var/lib/samurai/k276-standard-focus-r1/summary-private.json',timeout=15);summary=json.loads(q.stdout);assert summary['health']['passed'] and summary['error'] is None
photos=[]
for row in summary['runs']:
 item=row['jpeg'];target=P/('standard-focus-'+str(row['index'])+'-'+str(row['position'])+'-private.jpg');assert not target.exists();data=bytearray()
 for offset in range(0,item['bytes'],49152):
  length=min(49152,item['bytes']-offset);code='from pathlib import Path;import sys;f=Path(%r).open("rb");f.seek(%d);sys.stdout.buffer.write(f.read(%d))'%(item['path'],offset,length)
  part=host.ssh('python3 -c '+shlex.quote(code),timeout=20).stdout;assert len(part)==length;data.extend(part)
 assert hashlib.sha256(data).hexdigest()==item['sha256'];target.write_bytes(data);photos.append(dict(index=row['index'],position=row['position'],bytes=len(data),sha256=item['sha256'],path=str(target)))
(P/'standard-focus-photos-private.json').write_text(json.dumps(photos,indent=2)+'\n');print(json.dumps(dict(stage=276,private_photos_received=len(photos),all_hashes_verified=True)))
