from pathlib import Path
import importlib.util,json
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel241')
spec=importlib.util.spec_from_file_location('host241',R.parent/'kernel240/host.py')
host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
code=r'''
from pathlib import Path
import json,collections
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
p=r/'k241-loc-combined';state=json.loads((p/'state-private.json').read_text())
f=p/'events-private.jsonl';records=[]
if f.exists():
 for line in f.read_text().splitlines():
  try:records.append(json.loads(line))
  except json.JSONDecodeError:pass
phases=[dict(name=x['name'],applied=x.get('applied')) for x in records if x['kind']=='phase']
result=dict(state=state,phases=phases,records=len(records),commands=[{k:x[k] for k in ['message_id','ack_result','ack_error','indication_status']} for x in records if x['kind']=='command'])
if state['terminal'] and (p/'summary.json').exists():result['report']=json.loads((p/'summary.json').read_text())
print(json.dumps(result))
'''
run=host.ssh('python3 -',input=code.encode(),timeout=15)
(P/'combined-poll-host-private.json').write_bytes(run.stdout)
result=json.loads(run.stdout)
if 'report' in result:(R/'combined-validation.json').write_text(json.dumps(result['report'],indent=2)+'\n')
print(json.dumps(result))
