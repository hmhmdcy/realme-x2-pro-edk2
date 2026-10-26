from pathlib import Path
import json
import host
code=r'''
from pathlib import Path
import json
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes();p=r/'k238-controlled-rear-rgb-r14-r2';s=json.loads((p/'state-private.json').read_text())
if s['state']!='terminal':
 proc=Path('/proc',str(s['pid']));assert proc.exists() and proc.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==s['start_ticks']
report=json.loads((p/'summary.json').read_text()) if (p/'summary.json').exists() else None
print(json.dumps(dict(stage=238,state=s['state'],phase=s['phase'],exit_code=s.get('exit_code'),report=report)))
'''
r=host.ssh('python3 -',input=code.encode(),timeout=15);(host.PRIVATE/'controlled-rgb-capture-r2-poll-host-private.log').write_bytes(r.stdout+r.stderr);data=json.loads(r.stdout)
if data['state']=='terminal' and data['report'] is not None:
 report=data['report'];(Path(__file__).resolve().parent/'controlled-rear-rgb-r2-validation.json').write_text(json.dumps(report,indent=2)+'\n')
 p=host.PRIVATE/'current-work-private.json';s=json.loads(p.read_text());s.update(active_native_context=None,state='controlled capture terminal '+str(data['exit_code']),next='Inspect actual control metadata, write trace and cleanup; no blind same test replay.');p.write_text(json.dumps(s,indent=2)+'\n')
 print(json.dumps(dict(stage=238,exit_code=data['exit_code'],frames=len(report['frames']),passed=report['passed'],program_exit=report['program_exit'],worker_exception=report['worker_exception'],restored={k:report[k] for k in ['all_formats_restored','media_graph_restored','sensor_controls_restored','rails_unchanged','camera_devices_suspended','mclk1_mclk2_disabled','trace_instance_removed']},cpu_rgb_control_metadata_verified=report['cpu_rgb_control_metadata_verified'],candidate_core_and_ipa_mapped=report['candidate_core_and_ipa_mapped'],restore_errors=report['restore_errors'],taint=report['taint'],fault_delta=report['fault_delta'])))
else:print(json.dumps(data))
