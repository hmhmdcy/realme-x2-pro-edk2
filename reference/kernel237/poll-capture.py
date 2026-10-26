from pathlib import Path
import json,sys
import host
which,kind=sys.argv[1:];assert (which,kind) in [('rear','raw'),('front','raw'),('front','rgb')]
code=r'''
from pathlib import Path
import json,sys
which,kind=sys.argv[1:];r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
p=r/f'k237-capture-{which}-{kind}-r1';s=json.loads((p/'state-private.json').read_text())
if s['state']!='terminal':
 proc=Path('/proc',str(s['pid']));assert proc.exists() and proc.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==s['start_ticks']
report=json.loads((p/'summary.json').read_text()) if (p/'summary.json').exists() else None
print(json.dumps(dict(stage=237,state=s['state'],phase=s['phase'],exit_code=s.get('exit_code'),report=report)))
'''
r=host.ssh('python3 - '+which+' '+kind,input=code.encode(),timeout=12);(host.PRIVATE/f'{which}-{kind}-poll-host-private.log').write_bytes(r.stdout+r.stderr);data=json.loads(r.stdout)
if data['state']=='terminal' and data['report'] is not None:
 report=data['report'];(Path(__file__).resolve().parent/f'{which}-{kind}-capture-validation.json').write_text(json.dumps(report,indent=2)+'\n')
 p=host.PRIVATE/'current-work-private.json';s=json.loads(p.read_text());s.update(state=f'{which}/{kind} capture terminal '+str(data['exit_code']),active_native_context=None,next='Inspect real result before any next capture; complete front regression only after rear success.');p.write_text(json.dumps(s,indent=2)+'\n')
 print(json.dumps(dict(stage=237,camera=which,kind=kind,exit_code=data['exit_code'],frames=len(report['frames']),passed=report['passed'],program_exit=report['program_exit'],worker_exception=report['worker_exception'],formats_restored=report['all_formats_restored'],graph_restored=report['media_graph_restored'],controls_restored=report['sensor_controls_restored'],rails_restored=report['rails_unchanged'],pm_suspended=report['camera_devices_suspended'],mclks_off=report['mclk1_mclk2_disabled'],restore_errors=report['restore_errors'],taint=report['taint'],fault_delta=report['fault_delta'])))
else:print(json.dumps(data))
