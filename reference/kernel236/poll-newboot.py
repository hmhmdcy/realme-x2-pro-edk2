"""Observe the same native process; never relaunch on an observation failure."""
from pathlib import Path
import json
import host

code = r'''
from pathlib import Path
import json
out=Path('/var/lib/samurai/k236-runtime')
state=json.loads((out/'state-private.json').read_text())
report=dict(stage=236,state=state['state'])
if state['state']=='running':
 process=Path('/proc')/str(state['pid'])
 assert process.exists() and (process/'stat').read_text().rsplit(')',1)[1].split()[19]==state['start_ticks']
 report.update(observer_live=True,latest_observation=state.get('latest_observation'))
else:
 report['exit_code']=state['exit_code']
 if state['exit_code']==0:report['validation']=json.loads((out/'summary.json').read_text())
print(json.dumps(report))
'''
result = host.ssh('python3 -', input=code.encode(), timeout=20)
(host.PRIVATE / 'runtime-poll-host-private.json').write_bytes(result.stdout)
report = json.loads(result.stdout)
if report['state'] == 'terminal':
    state_path = host.PRIVATE / 'current-work-private.json'
    state = json.loads(state_path.read_text())
    state.update(active_native_session=None, active_native_context=None, runtime_observer_exit=report['exit_code'])
    if report['exit_code'] == 0:
        validation = report.pop('validation')
        (Path(__file__).resolve().parent / 'runtime-validation.json').write_text(json.dumps(validation, indent=2) + '\n')
        state.update(state='new boot candidate power/sensor/services observer passed; native RAW capture still pending',
                     next='Inspect real media graph and bounded rear RAW RAM statistics, PM/rail cleanup and front regression')
    else:
        state.update(state='single newboot observer failed; inspect retained failure/dmesg before any corrective operation',
                     next='Read existing native failure context; do not repeat observer or transition')
    state_path.write_text(json.dumps(state, indent=2) + '\n')
print(json.dumps(report))
