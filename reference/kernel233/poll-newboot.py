"""Observe the existing native readiness task, checking its live identity."""
from pathlib import Path
import json
import host

code = r'''
from pathlib import Path
import json
p=Path('/var/lib/samurai/k233-runtime');s=json.loads((p/'state-private.json').read_text())
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(p/'boot-id-private.txt').read_bytes()
if s['state']=='running':
 proc=Path('/proc')/str(s['pid']);assert proc.exists() and (proc/'stat').read_text().rsplit(')',1)[1].split()[19]==s['start_ticks']
 print(json.dumps(dict(state='running',worker_live=True,latest_observation=s.get('latest_observation'))))
else:
 print(json.dumps(dict(state='terminal',exit_code=s['exit_code'],summary=json.loads((p/'summary.json').read_text()) if s['exit_code']==0 else None)))
'''
result = host.ssh('python3 -', input=code.encode(), timeout=20)
(host.PRIVATE / 'runtime-poll-host-private.json').write_bytes(result.stdout)
report = json.loads(result.stdout)
if report['state'] == 'terminal':
    assert report['exit_code'] == 0, 'Inspect the recorded native observer failure; do not replay'
    summary = report['summary']
    (Path(__file__).resolve().parent / 'runtime-validation.json').write_text(json.dumps(summary, indent=2) + '\n')
    state = json.loads((host.PRIVATE / 'current-work-private.json').read_text())
    state.update(state='new PMIC modules/provider/P identity and automatic services verified',
                 active_native_context=None, active_native_session=None, runtime_deployed=True,
                 next='Verify Q warm/provider cold managed unbind cycles with no front client, then front RAM-only regression and final health')
    (host.PRIVATE / 'current-work-private.json').write_text(json.dumps(state, indent=2) + '\n')
print(json.dumps(report))
