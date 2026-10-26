"""Keep the photographed scene private; publish only decoding/statistical checks."""
from pathlib import Path
import hashlib,json
import host
r=host.ssh('cat /var/lib/samurai/k262-stills/front.jpg')
photo=host.PRIVATE/'front-private.jpg';photo.write_bytes(r.stdout)
code=r'''
import gi,hashlib,json,math
from pathlib import Path
gi.require_version('GdkPixbuf','2.0')
from gi.repository import GdkPixbuf
p=Path('/var/lib/samurai/k262-stills/front.jpg')
image=GdkPixbuf.Pixbuf.new_from_file(str(p))
scaled=image.scale_simple(128,72,GdkPixbuf.InterpType.BILINEAR)
rgb=scaled.get_pixels();stride=scaled.get_rowstride();channels=scaled.get_n_channels()
pixels=[tuple(rgb[y*stride+x*channels:y*stride+x*channels+3]) for y in range(72) for x in range(128)]
means=[sum(p[c] for p in pixels)/len(pixels) for c in range(3)]
std=[math.sqrt(sum((p[c]-means[c])**2 for p in pixels)/len(pixels)) for c in range(3)]
result=dict(stage=262,backend='PipeWire/libcamera -> wrappercamerabinsrc -> camerabin JPEG',jpeg_saved=True,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),decoded=True,width=image.get_width(),height=image.get_height(),sample_rgb_mean=means,sample_rgb_stddev=std,sample_min=min(map(min,pixels)),sample_max=max(map(max,pixels)),fraction_all_channels_le8=sum(max(p)<=8 for p in pixels)/len(pixels),fraction_all_channels_ge247=sum(min(p)>=247 for p in pixels)/len(pixels),scene_remains_private=True,gui_shutter_or_optical_colour_acceptance=False,image_done_message_receipt_available=False)
print(json.dumps(result))
'''
q=host.ssh('python3 -',input=code.encode())
d=json.loads(q.stdout);assert d['sha256']==hashlib.sha256(photo.read_bytes()).hexdigest()
d['private_export_sha256_verified']=True
(Path(__file__).parent/'front-photo-validation.json').write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps(d,indent=2))
