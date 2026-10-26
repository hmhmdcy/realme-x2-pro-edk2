"""Rank possible packed40 windows; heuristic evidence is never applied."""
from pathlib import Path
import json
import numpy as np
HERE=Path(__file__).resolve().parent;P=Path('E:/edk2-samurai-out/kernel320');P.mkdir(exist_ok=True)
raw=np.frombuffer(Path('E:/edk2-samurai-out/kernel299/imx319-eeprom-read1-private.bin').read_bytes(),np.uint8)
offsets=np.arange(len(raw)-1105+1)[:,None]
points=np.arange(221)[None,:]*5
high=raw[offsets+points+4].astype(np.uint16)
metrics=[];zeros=[]
for c in range(4):
 values=(raw[offsets+points+c].astype(np.uint16)+((high>>(6-2*c))&3)*256).astype(float)
 variance=values.var(axis=1);z=(values==0).sum(axis=1);zeros.append(z)
 grid=values.reshape(-1,13,17)
 energy=((np.diff(grid,axis=1)**2).sum(axis=(1,2))+(np.diff(grid,axis=2)**2).sum(axis=(1,2)))/(12*17+13*16)
 roughness=np.divide(energy,2*variance,out=np.full_like(variance,np.inf),where=variance>0)
 metrics.append(roughness)
metrics=np.stack(metrics,axis=1);zeros=np.stack(zeros,axis=1)
score=metrics.max(axis=1);score[(zeros>4).any(axis=1)]=np.inf
rank=np.argsort(score)
best=[]
for pos in rank:
 if not np.isfinite(score[pos]):break
 if any(abs(pos-r['offset'])<25 for r in best):continue
 best.append(dict(offset=int(pos),max_channel_roughness=float(score[pos]),channel_roughness=metrics[pos].tolist(),zero_samples=int(zeros[pos].sum())))
 if len(best)==8:break
report=dict(stage=320,declared_offset=208,declared_channel_roughness=metrics[208].tolist(),
 all_complete_windows_scanned=len(score),best_separated_windows=best,
 ranking_is_heuristic=True,layout_changed=False,individual_values_applied=False,phone_changed=False)
(P/'packed40-scan-private.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
