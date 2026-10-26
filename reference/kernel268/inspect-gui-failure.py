"""Read the owned window's diagnostics and actual camera state after a controller failure."""
import json
import sys
import host

code=r'''
from pathlib import Path
import json,re,subprocess
p=Path('/var/lib/samurai/k268-snapshot-gui');result={}
for name in ['stdout-private.json','stderr-private.txt','summary.json']:
 f=p/name
 if f.exists():
  text=f.read_text(errors='replace')
  if name=='stderr-private.txt':
   result['flow_counts']=dict(buffers=text.count('got new buffer'),renders=sum('gtk4paintablesink' in x and 'rendering object' in x for x in text.splitlines()))
   text='\n'.join(x for x in text.splitlines() if re.search(r'ERROR|WARN|error:|failed|Camera|camera|portal|permission|aperture',x,re.I))[-10000:]
  result[name]=text
for n in ['7-0010','9-0010']:result[n]=Path('/sys/bus/i2c/devices',n,'power/runtime_status').read_text().strip()
result['live_processes']=subprocess.run(['pgrep','-a','snapshot'],capture_output=True,text=True).stdout
print(json.dumps(result))
'''
if sys.argv[1:]:
 assert len(sys.argv)==2 and sys.argv[1] in ['r2','r3'];code=code.replace('k268-snapshot-gui','k268-snapshot-gui-'+sys.argv[1])
q=host.ssh('python3 -',input=code.encode(),timeout=20)
(host.PRIVATE/'gui-failure-details-private.json').write_bytes(q.stdout);d=json.loads(q.stdout)
for k,v in d.items():print(k+':\n'+str(v)[-6000:])
