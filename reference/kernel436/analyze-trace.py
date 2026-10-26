from pathlib import Path
import hashlib,json,sys
import numpy as np
from PIL import Image,ImageDraw

HERE=Path(__file__).resolve().parent
P=Path('E:/edk2-samurai-out/kernel436')
attempt=sys.argv[1] if len(sys.argv)>1 else 'r1'
assert attempt in ['r1','r3','r4','r5']
case=P/('runtime-collected-'+attempt)/'scene-native'
live=json.loads((HERE/('runtime-'+attempt+'-validation.json')).read_text())
assert live['state']['passed'] and not live['worker_live'] and not live['client_live']
trace=live['state']['captures']['scene-native']['trace'];sof=trace['sof']
def nv12(path):
 data=np.frombuffer(path.read_bytes(),np.uint8);assert data.size==460800
 y=data[:307200].reshape(480,640).astype(np.float32)
 uv=data[307200:].reshape(240,320,2).repeat(2,0).repeat(2,1).astype(np.float32)-128
 yy=1.164383*(y-16);u,v=uv[:,:,0],uv[:,:,1]
 rgb=np.stack([yy+1.596027*v,yy-.391762*u-.812968*v,yy+2.017232*u],-1)
 return y,uv,rgb.clip(0,255).astype(np.uint8)
rows=[];images=[]
for label,path in [('IFE FULL',case/f'tone-{sof}-full.nv12'),('IPE output',case/f'frame-{sof}.nv12')]:
 y,uv,rgb=nv12(path)
 image=Image.new('RGB',(640,510));image.paste(Image.fromarray(rgb),(0,30));ImageDraw.Draw(image).text((10,8),label,fill='white');images.append(image)
 target=P/(attempt+'-'+label.lower().replace(' ','-')+'-private.png');Image.fromarray(rgb).save(target)
 rows.append(dict(label=label,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),mean_y=float(y.mean()),min_y=float(y.min()),max_y=float(y.max()),mean_u=float(uv[:,:,0].mean()+128),mean_v=float(uv[:,:,1].mean()+128),rgb_mean=rgb.mean((0,1)).tolist()))
pair=Image.new('RGB',(1280,510))
for i,image in enumerate(images):pair.paste(image,(i*640,0))
pair.save(P/(attempt+'-same-sof-comparison-private.png'))
report=dict(stage=436,same_sof=sof,trace=trace,preview_decoder='BT.601 limited range for both stages; processing-domain diagnosis only, not colour accuracy',images=rows,absolute_image_quality_accepted=False,passed=True)
(P/(attempt+'-trace-pixel-metrics-private.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(stage=436,same_sof=sof,mean_y=[r['mean_y'] for r in rows],matched_inputs_and_output_saved=True,passed=True)))
