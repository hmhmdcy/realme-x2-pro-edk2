from pathlib import Path
import json
import host
R=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes();p=r/'k239-odm-source';s=json.loads((p/'state-private.json').read_text())
if s['state']!='terminal':
 proc=Path('/proc',str(s['pid']));assert proc.exists() and proc.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==s['start_ticks']
report=json.loads((p/'summary.json').read_text()) if (p/'summary.json').exists() else None
print(json.dumps(dict(stage=239,state=s['state'],phase=s['phase'],exit_code=s.get('exit_code'),mount_still_owned=s.get('mount_still_owned'),report=report)))
'''
result=host.ssh('python3 -',input=code.encode(),timeout=15);(host.PRIVATE/'odm-poll-host-private.log').write_bytes(result.stdout+result.stderr);data=json.loads(result.stdout)
if data['state']=='terminal':
 (R/'odm-validation.json').write_text(json.dumps(data,indent=2)+'\n')
 p=host.PRIVATE/'current-work-private.json';state=json.loads(p.read_text());state.update(active_native_context=None,state='ODM source worker terminal '+str(data['exit_code']),next='Inspect source report/cleanup; export only selected gps and properties privately if successful.');p.write_text(json.dumps(state,indent=2)+'\n')
print(json.dumps(data))
