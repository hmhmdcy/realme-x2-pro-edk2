from pathlib import Path
import json,subprocess
import host
code=b'''from pathlib import Path
import collections,json,re
out=Path('/var/lib/samurai/k191-assistance');lines=Path('/var/lib/samurai/k191-mm-deploy/daemon-debug-private.log').read_text().splitlines()
packets=[]
for i,line in enumerate(lines):
 name=next((s for s in ['Inject Predicted Orbits Data','Inject Xtra Data'] if 'message' in line and s.lower() in line.lower()),None)
 if name is None:continue
 flags=transaction=None
 for field in lines[max(0,i-12):i]:
  f=re.search(r'flags\\s+= "(none|response|indication)"',field);t=re.search(r'transaction = (\\d+)',field)
  if f:flags=f[1]
  if t:transaction=int(t[1])
 stop=next((j for j in range(i+1,min(i+500,len(lines))) if 'sent message...' in lines[j] or 'received message...' in lines[j]),min(i+500,len(lines)))
 part=None
 for j in range(i+1,stop):
  if 'type' in lines[j] and 'Part Number' in lines[j]:
   for field in lines[j+1:min(j+10,stop)]:
    m=re.search(r'translated = (?:"|\\x27)?(\\d+)',field)
    if m:part=int(m[1]);break
 packets.append(dict(name=name,type=flags,transaction=transaction,part=part,line_index=i))
(out/'wire-packets-private.json').write_text(json.dumps(packets,indent=2))
groups=collections.defaultdict(list)
for p in packets:groups[(p['name'],p['transaction'])].append(p)
orders=collections.Counter('/'.join(p['type'] or '?' for p in group) for group in groups.values())
counts=collections.Counter((p['name'],p['type']) for p in packets)
parts={typ:[p['part'] for p in packets if p['type']==typ and p['part'] is not None] for typ in ['none','indication']}
per_part=[]
for req in [p for p in packets if p['name']=='Inject Xtra Data' and p['type']=='none']:
 responses=[p for p in packets if p['name']==req['name'] and p['type']=='response' and p['transaction']==req['transaction']]
 indications=[p for p in packets if p['name']==req['name'] and p['type']=='indication' and p['part']==req['part']]
 assert len(responses)==len(indications)==1
 response=responses[0];indication=indications[0]
 per_part.append(dict(part=req['part'],order='indication/response' if indication['line_index']<response['line_index'] else 'response/indication',indication_transaction_matches_request=indication['transaction']==req['transaction']))
assert [p['part'] for p in per_part]==list(range(1,51))
report=dict(stage=191,packet_counts=[dict(message=k[0],type=k[1],count=v) for k,v in counts.items()],per_part_orders=dict(collections.Counter(p['order'] for p in per_part)),indications_with_matching_transaction=sum(p['indication_transaction_matches_request'] for p in per_part),request_part_numbers=parts['none'],indication_part_numbers=parts['indication'],
 chunk_debug_lines=sum('injecting predicted orbits data:' in x or 'injecting xtra data:' in x for x in lines))
(out/'wire-summary.json').write_text(json.dumps(report,indent=2)+'\\n');print(json.dumps(report))
'''
p=host.ssh('python3 -',input=code);report=json.loads(p.stdout)
(Path(__file__).resolve().parent/'injection-wire-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
