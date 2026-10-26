"""Observe the existing worker and collect the terminal audit without replay."""
from pathlib import Path
import json
import host

code = r'''
from pathlib import Path
import json
root=Path('/var/lib/samurai');out=root/'k236-quiesce-runner'
s=json.loads((out/'state-private.json').read_text())
if s['state']=='running':
 p=Path('/proc')/str(s['worker_pid']);assert p.exists()
 assert (p/'stat').read_text().rsplit(')',1)[1].split()[19]==s['worker_start_ticks']
 assert (Path('/proc')/str(s['child_pid'])).exists()
 report=dict(stage=236,state='running',worker_and_child_live=True)
else:
 report=dict(stage=236,state='terminal',exit_code=s['exit_code'])
 if s['exit_code']==0:
  report['validation']=json.loads((root/'k236-quiesce/quiesce-validation.json').read_text())
print(json.dumps(report))
'''
result = host.ssh('python3 -', input=code.encode(), timeout=20)
(host.PRIVATE / 'quiesce-poll-host-private.json').write_bytes(result.stdout)
report = json.loads(result.stdout)
if report['state'] == 'terminal':
    assert report['exit_code'] == 0, 'Inspect the terminal native worker log; do not replay'
    validation = report.pop('validation')
    (host.PRIVATE / 'quiesce-validation-private.json').write_text(json.dumps(validation, indent=2) + '\n')
    public = {k: v for k, v in validation.items() if k != 'boot_id'}
    (Path(__file__).resolve().parent / 'quiesce-validation.json').write_text(json.dumps(public, indent=2) + '\n')
    state = json.loads((host.PRIVATE / 'current-work-private.json').read_text())
    state.update(state='quiesce terminal0 and audit passed; ready for single bootloader transition',
                 active_native_session=None, active_native_context=None)
    (host.PRIVATE / 'current-work-private.json').write_text(json.dumps(state, indent=2) + '\n')
    report['quiesce_audit_pass'] = validation['quiesce_audit_pass']
print(json.dumps(report))
