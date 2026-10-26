from pathlib import Path
import json
import host

code = r'''
from pathlib import Path
import json
out=Path('/var/lib/samurai/k236-lab-fix');state=json.loads((out/'state-private.json').read_text())
report=dict(stage=236,state=state['state'],phase=state['phase'])
if state['state']=='running':
 process=Path('/proc')/str(state['pid'])
 assert process.exists() and (process/'stat').read_text().rsplit(')',1)[1].split()[19]==state['start_ticks']
 report.update(observer_live=True,latest_observation=state.get('latest_observation'))
else:
 report['exit_code']=state['exit_code']
 if (out/'summary.json').exists():report['validation']=json.loads((out/'summary.json').read_text())
print(json.dumps(report))
'''
result = host.ssh('python3 -', input=code.encode(), timeout=20)
(host.PRIVATE / 'lab-fix-poll-host-private.json').write_bytes(result.stdout)
report = json.loads(result.stdout)
if report['state'] == 'terminal':
    state_path = host.PRIVATE / 'current-work-private.json'
    state = json.loads(state_path.read_text())
    state.update(active_native_context=None, active_native_session=None, lab_fix_exit=report['exit_code'])
    if report['exit_code'] == 0:
        validation = report.pop('validation')
        (Path(__file__).resolve().parent / 'lab-fix-native-validation.json').write_text(json.dumps(validation, indent=2) + '\n')
        state.update(state='unbound lab replaced; rear identity/probe/autosuspend/rails-off passed; I2C trace analysis and RAW still pending',
                     next='Analyze existing ID trace, inspect media graph, bounded RAW RAM capture then front regression')
    else:
        state.update(state='same236 lab corrective observer terminal1; preserve failure and exact module state',
                     next='Inspect existing lab-fix failure context; do not repeat reload/reset/launch')
    state_path.write_text(json.dumps(state, indent=2) + '\n')
print(json.dumps(report))
