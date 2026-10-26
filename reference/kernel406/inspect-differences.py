"""Locate the mask-only pixel difference instead of calling it tuned output."""
from pathlib import Path
from collections import Counter
import json
import host
P=host.PRIVATE;C=P/'runtime-collected-r1';rows=[]
for w in [640,650]:
 n=w*480;read=lambda mode:(C/f'width-{w}-format-0-mode-{mode}-output-private.nv12').read_bytes();base=read(1);mask=read(4);dc=read(10);parts=[]
 for label,lo,hi,stride in [('Y',0,n,w),('UV',n,n*3//2,w)]:
  indices=[i-lo for i in range(lo,hi) if mask[i]!=base[i]];xs=Counter(i%stride for i in indices);ys=Counter(i//stride for i in indices)
  shifts=[]
  for first,last in [(0,160),(160,320),(320,480),(480,w)]:
   if first>=last:continue
   scores=[]
   for shift in range(-6,7):
    total=bad=0
    for y in range((hi-lo)//stride):
     for x in range(first,last):
      if 0<=x+shift<w:
       total+=1;bad+=mask[lo+y*stride+x]!=base[lo+y*stride+x+shift]
    scores.append((shift,bad,total))
   shifts.append(dict(first=first,last=last,best=sorted(scores,key=lambda r:r[1])[:3]))
  parts.append(dict(plane=label,differences=len(indices),x_hist=sorted(xs.items()),y_hist=sorted(ys.items()),region_shifts=shifts))
 row=dict(width=w,dc_enabled_matches_pair=dc==base,planes=parts);rows.append(row)
 print(json.dumps(dict(width=w,dc_enabled_matches_pair=dc==base,planes=[dict(plane=p['plane'],differences=p['differences'],x_ranges=[min(x for x,c in p['x_hist']),max(x for x,c in p['x_hist'])],most_common_x=sorted(p['x_hist'],key=lambda r:-r[1])[:12],region_shifts=p['region_shifts']) for p in parts])),flush=True)
(P/'mask-differences-private.json').write_text(json.dumps(rows,indent=2)+'\n')
