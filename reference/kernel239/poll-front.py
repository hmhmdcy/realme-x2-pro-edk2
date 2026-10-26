from pathlib import Path
import json,sys
import host
R=Path(__file__).resolve().parent;kind=sys.argv[1];assert kind in ['raw','rgb']
code=r'''
from pathlib import Path
import json,sys
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes();p=r/('k239-front-r15-'+sys.argv[1]);s=json.loads((p/'state-private.json').read_text())
if s['state']!='terminal':
 proc=Path('/proc',str(s['pid']));assert proc.exists() and proc.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==s['start_ticks']
report=json.loads((p/'summary.json').read_text()) if (p/'summary.json').exists() else None
print(json.dumps(dict(stage=239,state=s['state'],phase=s['phase'],exit_code=s.get('exit_code'),report=report)))
'''
result=host.ssh('python3 - '+kind,input=code.encode(),timeout=15);(host.PRIVATE/f'front-{kind}-poll-host-private.log').write_bytes(result.stdout+result.stderr);data=json.loads(result.stdout)
if data['state']=='terminal' and data['report'] is not None:
 report=data['report'];(R/f'front-{kind}-validation.json').write_text(json.dumps(report,indent=2)+'\n')
 p=host.PRIVATE/'current-work-private.json';state=json.loads(p.read_text());state.update(active_native_context=None,state='Front r15 '+kind+' terminal '+str(data['exit_code']));p.write_text(json.dumps(state,indent=2)+'\n')
 print(json.dumps(dict(stage=239,kind=kind,passed=report['passed'],frames=len(report['frames']),candidate_mapped=report['candidate_core_and_ipa_mapped'],restore_errors=report['restore_errors'],fault_delta=report['fault_delta'])))
else:print(json.dumps(data))
