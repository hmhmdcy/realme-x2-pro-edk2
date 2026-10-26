from pathlib import Path
import hashlib,json
from PIL import Image,ImageStat
R=Path(__file__).parent;P=Path('E:/edk2-samurai-out/kernel265');photos=json.loads((P/'gui-capture-private.json').read_text())['new_jpegs']
for i,photo in enumerate(photos):
 p=P/('snapshot-photo-'+str(i)+'-private.jpeg');assert p.stat().st_size==photo['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==photo['sha256']
 with Image.open(p) as image:assert image.format=='JPEG';image.verify()
 with Image.open(p) as image:
  image.load();stats=ImageStat.Stat(image.convert('RGB').resize((128,72)))
  result=dict(stage=265,camera=photo['camera'],jpeg_bytes=p.stat().st_size,sha256=photo['sha256'],width=image.width,height=image.height,decoded=True,rgb_mean=stats.mean,optical_quality_not_accepted=True,photo_kept_private=True)
 (R/('snapshot-photo-'+str(i)+'-validation.json')).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

