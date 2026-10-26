"""Decode the privately exported actual GUI shutter image without publishing pixels."""
from pathlib import Path
import hashlib,json
from PIL import Image,ImageStat
R=Path(__file__).parent;photo=Path('E:/edk2-samurai-out/kernel264/snapshot-photo-0-private.jpeg')
proof=json.loads((R/'snapshot-photo-0-validation.json').read_text());assert hashlib.sha256(photo.read_bytes()).hexdigest()==proof['sha256']
im=Image.open(photo);im.load();stats=ImageStat.Stat(im.convert('RGB').resize((128,72)))
report=dict(stage=264,jpeg_bytes=photo.stat().st_size,sha256=proof['sha256'],exported_and_hash_verified=True,decoder='Pillow',width=im.width,height=im.height,decoded=True,rgb_mean=stats.mean,optical_quality_not_accepted=True,photo_kept_private=True)
(R/'snapshot-photo-0-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
