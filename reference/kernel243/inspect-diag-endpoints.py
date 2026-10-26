from pathlib import Path
import json,struct
r=Path('/var/lib/samurai');out={};private={}
for name in ['k243-diag-passive-r3','k243-diag-query-r2','k243-gnss-diag']:
 rows=[json.loads(x) for x in (r/name/'events-private.jsonl' if name!='k243-gnss-diag' else r/name/'diag-events-private.jsonl').read_text().splitlines()]
 private[name]=rows
 entries=[]
 for x in rows:
  if x.get('kind')!='rx':continue
  b=bytes.fromhex(x['hex'])
  if x.get('port')==0xfffffffe and len(b)==20:
   cmd,service,instance,node,port=struct.unpack('<IIIII',b)
   if service==4097:entries.append(dict(command=cmd,instance=instance,node=node,port=port))
 out[name]=entries
print(json.dumps({'report':out,'private':private}))
