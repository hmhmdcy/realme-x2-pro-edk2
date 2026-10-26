from pathlib import Path
import hashlib,json
import numpy as np
from PIL import Image,ImageDraw
HERE=Path(__file__).resolve().parent;P=Path('E:/edk2-samurai-out/kernel436')
live=json.loads((HERE/'runtime-r2-validation.json').read_text());assert live['state']['passed'] and not live['worker_live'] and not live['client_live']
folder=P/'runtime-collected-r2/replay'
def decode(path):
 d=np.frombuffer(path.read_bytes(),np.uint8);assert d.size==460800
 y=d[:307200].reshape(480,640).astype(np.float32);uv=d[307200:].reshape(240,320,2).repeat(2,0).repeat(2,1).astype(np.float32)-128
 yy=(y-16)*1.164383;u,v=uv[:,:,0],uv[:,:,1]
 rgb=np.stack([yy+v*1.596027,yy-u*.391762-v*.812968,yy+u*2.017232],-1).clip(0,255).astype(np.uint8)
 return d,y,uv,rgb
names=['stock','LTM off','colour only','bypass','repeat stock'];rows=[];canvas=Image.new('RGB',(1280,1020))
source=P/'runtime-collected-r1/scene-native/frame-12.nv12'
for i,name in enumerate(names):
 path=folder/f'mode-{i}-output-private.bin';d,y,uv,rgb=decode(path)
 Image.fromarray(rgb).save(P/('replay-'+str(i)+'-private.png'))
 rows.append(dict(mode=i,label=name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),mean_y=float(y.mean()),mean_u=float(uv[:,:,0].mean()+128),mean_v=float(uv[:,:,1].mean()+128),equal_live_output=path.read_bytes()==source.read_bytes()))
 if i<4:
  x=(i%2)*640;yy=(i//2)*510;canvas.paste(Image.fromarray(rgb),(x,yy+30));ImageDraw.Draw(canvas).text((x+10,yy+8),name,fill='white')
assert rows[0]['sha256']==rows[4]['sha256']
canvas.save(P/'tone-replay-comparison-private.png')
r=dict(stage=436,same_sof_input=12,physical_ipe_jobs=5,input_full_and_pd10_immutable=True,stock_cold_repeat_equal=True,replay_stock_equals_live=rows[0]['equal_live_output'],images=rows,absolute_image_quality_accepted=False,passed=True)
(P/'replay-pixel-metrics-private.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(r,indent=2))
