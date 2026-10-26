from pathlib import Path
import json
import host
R=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
p=r/'k240-snapshot-cairo';s=json.loads((p/'state-private.json').read_text())
if s['state']!='terminal':
 proc=Path('/proc',str(s['pid']));assert proc.exists() and proc.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==s['start_ticks']
report=json.loads((p/'summary.json').read_text()) if s['state']=='terminal' and (p/'summary.json').exists() else None
logs={}
if s['state']=='terminal':
 for leaf in ['stderr-private.txt','failure-private.txt','stdout-private.json']:
  q=p/leaf
  if q.is_file():logs[leaf]=q.read_text(errors='replace')[-20000:]
print(json.dumps(dict(state=s['state'],phase=s['phase'],report=report,logs=logs)))
'''
result=host.ssh('python3 -',input=code.encode(),timeout=15)
(host.PRIVATE/'snapshot-cairo-poll-host-private.log').write_bytes(result.stdout+result.stderr)
data=json.loads(result.stdout)
if data['state']=='terminal':
 (host.PRIVATE/'snapshot-cairo-gui-logs-private.json').write_text(json.dumps(data['logs'],indent=2)+'\n')
 if data['report']:(R/'snapshot-cairo-startup-validation.json').write_text(json.dumps(data['report'],indent=2)+'\n')
 p=host.PRIVATE/'current-work-private.json';state=json.loads(p.read_text());state.update(active_native_context=None,state='Snapshot CPU-rendered diagnostic terminal',next='Inspect actual frame/render evidence and fault deltas before any desktop launcher change')
 p.write_text(json.dumps(state,indent=2)+'\n')
 print(json.dumps({k:v for k,v in data.items() if k!='logs'}))
else:print(json.dumps({k:v for k,v in data.items() if k!='logs'}))
