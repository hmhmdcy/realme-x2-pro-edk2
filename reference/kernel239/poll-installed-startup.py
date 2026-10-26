from pathlib import Path
import json
import host
R=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes();p=r/'k239-r15-installed-startup';s=json.loads((p/'state-private.json').read_text())
if s['state']!='terminal':
 proc=Path('/proc',str(s['pid']));assert proc.exists() and proc.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==s['start_ticks']
report=json.loads((p/'summary.json').read_text()) if (p/'summary.json').exists() else None
logs={}
if s['state']=='terminal':
 lines=(p/'stderr-private.txt').read_text(errors='replace').splitlines()
 logs={name:[line for line in lines if pattern in line] for name,pattern in [('processing','Processing frame '),('debayer','Debayer parameters:'),('blc','Auto-set black level:'),('captured','Captured request') ]}
print(json.dumps(dict(stage=239,state=s['state'],phase=s['phase'],exit_code=s.get('exit_code'),report=report,logs=logs)))
'''
result=host.ssh('python3 -',input=code.encode(),timeout=15);(host.PRIVATE/'r15-installed-startup-poll-host-private.log').write_bytes(result.stdout+result.stderr);data=json.loads(result.stdout)
if data['state']=='terminal' and data['report'] is not None:
 report=data['report'];(R/'r15-installed-startup-validation.json').write_text(json.dumps(report,indent=2)+'\n');(host.PRIVATE/'r15-installed-startup-parameter-log-lines-private.json').write_text(json.dumps(data['logs'],indent=2)+'\n')
 state_path=host.PRIVATE/'current-work-private.json';state=json.loads(state_path.read_text());state.update(active_native_context=None,state='r15 two-startup RGB diagnostic terminal '+str(data['exit_code']),next='Analyze actual12 Debayer parameters vs output FIFO and IPA metadata; paired RAW/RGB if required.');state_path.write_text(json.dumps(state,indent=2)+'\n')
 print(json.dumps(dict(stage=239,exit_code=data['exit_code'],frames=len(report['frames']),diagnostic_completed=report['diagnostic_capture_completed'],strict_nonzero=report['strict_nonzero_frames_passed'],zero_indices=[f['queued_index'] for f in report['frames'] if f['all_zero']],debayer_log_count=len(data['logs']['debayer']),blc_log_count=len(data['logs']['blc']),captured_log_count=len(data['logs']['captured']),restore_errors=report['restore_errors'],fault_delta=report['fault_delta'])))
else:print(json.dumps(data))
