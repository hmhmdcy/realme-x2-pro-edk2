from pathlib import Path
import bisect,json,re,struct
import host
P=host.PRIVATE;names=[]
for line in (P.parent/'kernel350/hal-symbols-private.txt').read_text().splitlines():
 fields=line.split(' ',2)
 if len(fields)==3:
  try:names.append((int(fields[0],16),fields[2]))
  except ValueError:pass
names.sort();addresses=[x[0] for x in names]
def symbol(pc):
 i=bisect.bisect_right(addresses,pc)-1
 return names[i][1]+'+'+hex(pc-names[i][0]) if i>=0 else hex(pc)
lines=[]
for slug in ['640x480-p8-c1','1920x1080-p8-c1','4608x3456-p8-c1']:
 blob=(P/(slug+'-stripe-private.bin')).read_bytes();writes=json.loads((P/(slug+'-writes-private.json')).read_text());last={}
 for row in writes:
  for off in range(row['offset'],row['offset']+row['size']):last[off]=row['pc']
 lines.append(slug)
 for begin,end in [(0,436),(2268,2892)]:
  for off in range(begin,end,2):
   v=struct.unpack_from('<H',blob,off)[0]
   if v and v!=0xa5a5:
    lines.append(f'{off:5d} +{off-begin:3d} {v:5d} {v:#06x} {symbol(last[off]) if off in last else "provider/copy"}')
(P/'field-inspection-private.txt').write_text('\n'.join(lines)+'\n');print('Retained compact nonzero header/pass/stripe fields with original producer PCs.')
