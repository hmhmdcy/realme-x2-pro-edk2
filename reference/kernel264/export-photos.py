from pathlib import Path
import hashlib,json,shlex
import host
R=Path(__file__).parent
photos=json.loads((host.PRIVATE/'gui-capture-private.json').read_text())['new_jpegs']
for i,photo in enumerate(photos):
 code="from pathlib import Path;import sys;sys.stdout.buffer.write(Path("+repr(photo['path'])+").read_bytes())"
 q=host.ssh('python3 -c '+shlex.quote(code),timeout=25);assert len(q.stdout)==photo['bytes'] and hashlib.sha256(q.stdout).hexdigest()==photo['sha256'];target=host.PRIVATE/('snapshot-photo-'+str(i)+'-private.jpeg');assert not target.exists();target.write_bytes(q.stdout)
 try:
  from PIL import Image,ImageStat
  im=Image.open(target);im.load();stats=ImageStat.Stat(im.convert('RGB').resize((128,72)))
  result=dict(stage=264,jpeg_bytes=len(q.stdout),sha256=photo['sha256'],width=im.width,height=im.height,decoded=True,rgb_mean=stats.mean,optical_quality_not_accepted=True,photo_kept_private=True)
 except ImportError:result=dict(stage=264,jpeg_bytes=len(q.stdout),sha256=photo['sha256'],exported_and_hash_verified=True,decoder_not_available=True,photo_kept_private=True)
 (R/('snapshot-photo-'+str(i)+'-validation.json')).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
