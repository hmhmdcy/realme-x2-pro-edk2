from pathlib import Path
import hashlib,json,re
import numpy as np
from PIL import Image,ImageDraw
HERE=Path(__file__).resolve().parent;P=Path('E:/edk2-samurai-out/kernel438');root=P/'runtime-collected-r1'
state=json.loads((root/'state.json').read_text());assert state['passed']
rows=[];canvas=Image.new('RGB',(1280,510))
for index,(name,summary) in enumerate(state['captures'].items()):
 case=root/name;text=(case/'client.log').read_text();assert '640x480-NV12/sYCC' in text
 path=sorted(case.glob('frame-*.nv12'),key=lambda p:int(p.stem.split('-')[1]))[-1]
 d=np.frombuffer(path.read_bytes(),np.uint8);assert d.size==460800
 y=d[:307200].reshape(480,640).astype(np.float32);uv=d[307200:].reshape(240,320,2).repeat(2,0).repeat(2,1).astype(np.float32)-128;u,v=uv[:,:,0],uv[:,:,1]
 rgb=np.stack([y+1.402*v,y-.344136*u-.714136*v,y+1.772*u],-1).clip(0,255).astype(np.uint8)
 image=Image.fromarray(rgb);image.save(P/(summary['model']+'-last-private.png'));canvas.paste(image,(index*640,30));ImageDraw.Draw(canvas).text((index*640+10,8),summary['model'],fill='white')
 rows.append(dict(model=summary['model'],last_sof=int(path.stem.split('-')[1]),source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),mean_y=float(y.mean()),mean_u=float(uv[:,:,0].mean()+128),mean_v=float(uv[:,:,1].mean()+128)))
canvas.save(P/'rear-scenes-private.png')
(P/'scene-pixel-metrics-private.json').write_text(json.dumps(dict(rows=rows,preview_decoder='BT.601 full range, matching sYCC stream metadata; not colour calibration',absolute_image_quality_accepted=False),indent=2)+'\n')
print(json.dumps(dict(models=[r['model'] for r in rows],private_previews_saved=True,absolute_image_quality_accepted=False)))
