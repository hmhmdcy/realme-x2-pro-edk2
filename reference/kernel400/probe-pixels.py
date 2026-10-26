"""Inspect synthetic hardware samples without exposing factory tables or images."""
from pathlib import Path
from collections import Counter
import json,statistics,zlib
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;C=P/'runtime-collected-r1';N=640*480
state=json.loads((HERE/'runtime-validation.json').read_text())['state'];assert state['passed']
def canonical(blob,fmt):
 if not fmt:return blob
 out=bytearray(blob);out[N::2]=blob[N+1::2];out[N+1::2]=blob[N::2];return bytes(out)
def samples(blob):
 out=[]
 for row in range(6):
  for col in range(8):
   pixels=[[blob[(row*80+y)*640+col*80+x] for y in range(16,64) for x in range(16,64)],*[ [blob[N+(row*40+y)*640+col*80+x+channel] for y in range(8,32) for x in range(16,64,2)] for channel in range(2)]]
   out.append(dict(row=row,col=col,median=[statistics.median(p) for p in pixels],range=[[min(p),max(p)] for p in pixels]))
 return out
images={};patches={}
for fmt in range(2):
 for mode in range(8):
  b=(C/f'format-{fmt}-mode-{mode}-output-private.nv12').read_bytes();assert len(b)==N*3//2
  # The native client starts CRC at zero and omits the conventional complements.
  actual=zlib.crc32(b,0xffffffff)^0xffffffff
  row=next(r for r in state['native_cases'][:-1] if r['format']==fmt and r['mode']==mode);assert actual==row['output_crc']
  images[fmt,mode]=canonical(b,fmt);patches[fmt,mode]=samples(images[fmt,mode])
report=[]
for mode in range(8):
 a=images[0,mode];b=images[1,mode]
 report.append(dict(mode=mode,nv12_nv21_normalized_different=sum(x!=y for x,y in zip(a,b)),y_values=sorted(set(a[:N])) if mode==3 else None,uv_values=sorted(set(a[N:])) if mode==3 else None))
stats={}
for plane,start,end in [('y',0,N),('uv',N,N*3//2)]:
 a=images[0,2][start:end];half=images[0,4][start:end];zero=images[0,3][start:end]
 twice=Counter(2*h-p-z for h,p,z in zip(half,a,zero));stats[plane]=dict(half_twice_error_histogram=dict(sorted(twice.items())),max_abs_half_twice_error=max(map(abs,twice)))
delta=[]
for index in range(48):
 p=patches[0,2][index]['median'];a=patches[0,6][index]['median'];b=patches[0,7][index]['median'];delta.append(dict(row=index//8,col=index%8,positive=[x-y for x,y in zip(a,p)],negative=[x-y for x,y in zip(b,p)],sum_error=[x+y-2*z for x,y,z in zip(a,b,p)]))
(P/'patches-private.json').write_text(json.dumps({f'{f}-{m}':v for (f,m),v in patches.items()},indent=2)+'\n');(P/'offset-patch-deltas-private.json').write_text(json.dumps(delta,indent=2)+'\n')
print(json.dumps(dict(formats=report,pair_identity_different=sum(x!=y for x,y in zip(images[0,1],images[0,2])),half=stats,interior_offset_y_deltas=sorted(set(d['positive'][0] for d in delta if 1<=d['row']<=3)),interior_opposite_offset_y_sum_errors=sorted(set(d['sum_error'][0] for d in delta if 1<=d['row']<=3))),indent=2))
