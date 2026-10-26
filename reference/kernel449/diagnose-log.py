"""Locate mixed records in retained private logs without touching the device."""
import re
from pathlib import Path
import host

for name in ['user-cancel-1080', 'user-sustained-1080']:
 lines=(host.PRIVATE/'runtime-collected-r2'/name/'client.log').read_text().splitlines()
 seen=set();receipts=set();failures=[]
 for i,line in enumerate(lines):
  v=dict(re.findall(r'([a-z][a-z0-9-]*)=([^ ]+)',line))
  if 'IPE_OBSERVE ' in line:seen.add(int(v['token']))
  if 'IPE_RECEIPT ' in line:
   token=int(v['token'])
   if token not in seen or token in receipts:failures.append(i)
   receipts.add(token)
 print(name,'lines',len(lines),'observations',len(seen),'receipts',len(receipts),'mismatches',len(failures))
 for i in failures[:3]:
  print('\n'.join(str(j)+':'+lines[j] for j in range(max(0,i-3),min(len(lines),i+3))))
