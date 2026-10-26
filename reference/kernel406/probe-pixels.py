"""Observe saved hardware pixels without assuming the LTM transfer equation."""
from pathlib import Path
from collections import Counter
import binascii,json,statistics
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;C=P/'runtime-collected-r1'
state=json.loads((C/'state.json').read_text());assert len(state['native_cases'])==53
images={};rows=[]
for width in [640,650]:
 n=width*480;size=n*3//2
 for fmt in [0,1]:
  for mode in range(13):
   blob=(C/f'width-{width}-format-{fmt}-mode-{mode}-output-private.nv12').read_bytes();assert len(blob)==size
   case=next(r for r in state['native_cases'][:-1] if r['width']==width and r['format']==fmt and r['mode']==mode);assert (binascii.crc32(blob,0xffffffff)^0xffffffff)==case['output_crc']
   if fmt:
    canonical=bytearray(blob);canonical[n::2]=blob[n+1::2];canonical[n+1::2]=blob[n::2];blob=bytes(canonical)
   images[width,fmt,mode]=blob
 for mode in range(13):
  image=images[width,0,mode];pair=images[width,0,1];gray=[]
  for col in range(8):
   patch=[image[y*width+x] for y in range(16,64) for x in range(col*80+16,col*80+64)];gray.append(statistics.median(patch))
  row=dict(width=width,mode=mode,different_from_pair=sum(a!=b for a,b in zip(image,pair)),max_abs_from_pair=max(abs(a-b) for a,b in zip(image,pair)),different_formats=sum(a!=b for a,b in zip(image,images[width,1,mode])),y_range=[min(image[:n]),max(image[:n])],uv_range=[min(image[n:]),max(image[n:])],y_most_common=Counter(image[:n]).most_common(8),gray_patch_y=gray)
  rows.append(row);print(json.dumps(row),flush=True)
(P/'pixel-probe-private.json').write_text(json.dumps(rows,indent=2)+'\n')
