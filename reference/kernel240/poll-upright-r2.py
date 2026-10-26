from pathlib import Path
import hashlib
import json
import host

R=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import hashlib,json
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
p=r/'k240-upright-paired-r15-r2';s=json.loads((p/'state-private.json').read_text())
if s['state']!='terminal':
 proc=Path('/proc',str(s['pid']));assert proc.exists() and proc.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==s['start_ticks']
report=(p/'summary.json').read_bytes() if s['state']=='terminal' and (p/'summary.json').exists() else None
logs={}
if s['state']=='terminal':
 lines=(p/'stderr-private.txt').read_text(errors='replace').splitlines()
 logs={name:[line for line in lines if pattern in line] for name,pattern in [('processing','Processing frame '),('debayer','Debayer parameters:'),('blc','Auto-set black level:'),('captured','Captured request')]}
print(json.dumps(dict(stage=240,state=s['state'],phase=s['phase'],exit_code=s.get('exit_code'),
 summary_bytes=len(report) if report else 0,summary_sha256=hashlib.sha256(report).hexdigest() if report else None,logs=logs)))
'''
result=host.ssh('python3 -',input=code.encode(),timeout=15)
(host.PRIVATE/'upright-r2-poll-host-private.log').write_bytes(result.stdout+result.stderr)
data=json.loads(result.stdout)
if data['state']!='terminal':
 print(json.dumps({k:v for k,v in data.items() if k!='logs'}));raise SystemExit(0)
assert data['summary_bytes']>0
payload=bytearray()
for start in range(0,data['summary_bytes'],48*1024):
 count=min(48*1024,data['summary_bytes']-start)
 read="from pathlib import Path;import sys;f=Path('/var/lib/samurai/k240-upright-paired-r15-r2/summary.json').open('rb');f.seek(%d);sys.stdout.buffer.write(f.read(%d));f.close()"%(start,count)
 block=host.ssh('python3 -',input=read.encode(),timeout=25).stdout;assert len(block)==count;payload.extend(block)
assert hashlib.sha256(payload).hexdigest()==data['summary_sha256']
report=json.loads(payload)
(R/'upright-r2-validation.json').write_text(json.dumps(report,indent=2)+'\n')
(host.PRIVATE/'upright-r2-parameter-log-lines-private.json').write_text(json.dumps(data['logs'],indent=2)+'\n')
state_path=host.PRIVATE/'current-work-private.json';state=json.loads(state_path.read_text())
state.update(state='Upright paired24 diagnostic terminal '+str(data['exit_code']),active_native_context=None,
    next='Analyze paired RAW/RGB distributions and both exposures; preserve strict black frames and all cleanup results')
state_path.write_text(json.dumps(state,indent=2)+'\n')
print(json.dumps(dict(stage=240,state=data['state'],exit_code=data['exit_code'],frames=len(report['frames']),
    diagnostic_completed=report['diagnostic_capture_completed'],strict_nonzero=report['strict_nonzero_frames_passed'],
    zero_indices=[f['queued_index'] for f in report['frames'] if f['all_zero']],
    processing_log_count=len(data['logs']['processing']),debayer_log_count=len(data['logs']['debayer']),
    restore_errors=report['restore_errors'],fault_delta=report['fault_delta'])))
