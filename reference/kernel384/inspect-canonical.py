"""Private comparison of consumed, deterministic striping fields."""
from pathlib import Path
import json,struct
P=Path('/mnt/e/edk2-samurai-out/kernel383')
OUT=P.parent/'kernel384';OUT.mkdir(mode=0o700,exist_ok=True)
cases=[]
for w,h in [(640,480),(1920,1080),(4608,3456)]:
 for p,c in [(8,1),(8,2),(9,1),(9,2)]:
  slug=f'{w}x{h}-p{p}-c{c}'
  blob=(P/(slug+'-canonical-stripe-private.bin')).read_bytes()
  reads=json.loads((P/(slug+'-reads-private.json')).read_text())
  cases.append((slug,blob,{int(k):v for k,v in reads.items()}))
lines=[]
for start,size in [(0,2268),(2268,624)]:
 lines.append(f'AREA {start} cases '+','.join(x[0] for x in cases))
 for off in range(start,start+size,2):
  vals=[struct.unpack_from('<H',blob,off)[0] for _,blob,_ in cases]
  consumed=any(off in reads or off+1 in reads for _,_,reads in cases)
  if any(vals) and consumed:
   pcs=sorted({pc for _,_,r in cases for byte in [off,off+1] for pc in r.get(byte,[])})
   lines.append(f'{off-start:4d} '+','.join(str(v) for v in vals)+' readers '+','.join(hex(v) for v in pcs))
(OUT/'consumed-fields-private.txt').write_text('\n'.join(lines)+'\n')
print('Private consumed-field comparison retained for 12 cases.')
