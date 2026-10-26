import host,json
code=r'''
from pathlib import Path
import json
root=Path('/var/lib/samurai');out=root/'k222-sof-trial';state=json.loads((out/'state-private.json').read_text())
r=dict(phase=state['phase'],commands=state['commands'],same_boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k222-baseline/boot-id-private.txt').read_bytes(),taint=int(Path('/proc/sys/kernel/tainted').read_text()))
for name in ['gap-runner-stdout-private.json','gap-runner-stderr-private.txt']:
 if (out/name).exists():
  value=(out/name).read_text()
  if name.endswith('.json'):
   try:r['gap_summary']=json.loads(value)
   except ValueError:r['invalid_summary']=True
  else:r['runner_error']=value[-3500:]
if (out/'events-private.json').exists():
 rows=json.loads((out/'events-private.json').read_text());r.update(events=len(rows),first=rows[0] if rows else None,last=rows[-1] if rows else None)
print(json.dumps(r))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=30);(host.PRIVATE/'sof-trial-inspection-private.json').write_bytes(p.stdout+p.stderr);print(p.stdout.decode())
