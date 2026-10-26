"""Inspect saved synthetic Gamma pixels and keep full per-patch values private."""
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
   pixels=[[blob[(row*80+y)*640+col*80+x] for y in range(16,64) for x in range(16,64)],*[[blob[N+(row*40+y)*640+col*80+x+channel] for y in range(8,32) for x in range(16,64,2)] for channel in range(2)]]
   out.append(dict(row=row,col=col,median=[statistics.median(p) for p in pixels],range=[[min(p),max(p)] for p in pixels]))
 return out
images={};patches={};rows=[]
for fmt in range(2):
 for mode in range(10):
  b=(C/f'format-{fmt}-mode-{mode}-output-private.nv12').read_bytes();assert len(b)==N*3//2
  row=next(r for r in state['native_cases'][:-1] if r['format']==fmt and r['mode']==mode);assert (zlib.crc32(b,0xffffffff)^0xffffffff)==row['output_crc']
  images[fmt,mode]=canonical(b,fmt);patches[fmt,mode]=samples(images[fmt,mode])
for mode in range(10):
 a=images[0,mode];b=images[1,mode]
 rows.append(dict(mode=mode,nv12_nv21_normalized_different=sum(x!=y for x,y in zip(a,b)),vs_pair_different=sum(x!=y for x,y in zip(a,images[0,1])),y_min=min(a[:N]),y_max=max(a[:N]),uv_min=min(a[N:]),uv_max=max(a[N:]),gray_y=[p['median'][0] for p in patches[0,mode][:8]],gray_uv=[p['median'][1:] for p in patches[0,mode][:1]]))
stats={}
for label,start,end in [('Y',0,N),('UV',N,N*3//2)]:
 error=Counter(2*h-p-z for h,p,z in zip(images[0,4][start:end],images[0,2][start:end],images[0,3][start:end]));stats[label]=dict(twice_error_histogram=dict(sorted(error.items())),max_abs_twice_error=max(map(abs,error)))
previous=(P.parent/'kernel400/runtime-collected-r1/format-0-mode-2-output-private.nv12').read_bytes()
out=dict(stage=402,formats=rows,generic20_vs_previous_generic0_different_bytes=sum(a!=b for a,b in zip(images[0,1],previous)),identity_gamma_vs_pair_max_abs=max(abs(a-b) for a,b in zip(images[0,2],images[0,1])),half_about_zero=stats,completed=True)
(P/'patches-private.json').write_text(json.dumps({f'{f}-{m}':v for (f,m),v in patches.items()},indent=2)+'\n')
(P/'pixel-probe-private.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
