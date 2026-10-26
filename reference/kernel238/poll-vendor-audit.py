from pathlib import Path
import json
import host
code=r'''
from pathlib import Path
import json
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes();p=r/'k238-vendor-audit';s=json.loads((p/'state-private.json').read_text())
if s['state']!='terminal':
 proc=Path('/proc',str(s['pid']));assert proc.exists() and proc.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==s['start_ticks']
report=json.loads((p/'summary.json').read_text()) if (p/'summary.json').exists() else None
print(json.dumps(dict(stage=238,state=s['state'],phase=s['phase'],exit_code=s.get('exit_code'),mount_still_owned=s.get('mount_still_owned'),report=report)))
'''
r=host.ssh('python3 -',input=code.encode(),timeout=12);(host.PRIVATE/'vendor-poll-host-private.log').write_bytes(r.stdout+r.stderr);data=json.loads(r.stdout)
if data['state']=='terminal':
 (Path(__file__).resolve().parent/'vendor-audit-validation.json').write_text(json.dumps(data,indent=2)+'\n');p=host.PRIVATE/'current-work-private.json';s=json.loads(p.read_text());s.update(active_native_context=None,vendor_audit_exit=data['exit_code']);p.write_text(json.dumps(s,indent=2)+'\n')
print(json.dumps(data))
