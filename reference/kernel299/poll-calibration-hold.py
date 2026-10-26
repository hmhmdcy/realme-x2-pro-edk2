"""Observe the same physical capture worker and preserve failures."""
from pathlib import Path
import json
import host
ROOT=Path(__file__).resolve().parent
identity=json.loads((host.PRIVATE/'calibration-hold-launch-private.json').read_text())
code=r'''
from pathlib import Path
import json
root=Path('/var/lib/samurai/k299-eeprom-r1');state=json.loads((root/'state-private.json').read_text());assert state['pid']==identity['pid']
p=Path('/proc',str(identity['pid']));live=False
if p.exists():
 f=(p/'stat').read_text().rsplit(')',1)[1].split();live=f[19]==identity['start_ticks'] and f[0]!='Z'
child=Path('/proc',str(state.get('child_pid',0)));child_live=False
if child.exists():
 f=(child/'stat').read_text().rsplit(')',1)[1].split();child_live=f[19]==state.get('child_start_ticks') and f[0]!='Z'
print(json.dumps(dict(state=state,matching_worker_live=live,matching_power_owner_live=child_live,
 summary=json.loads((root/'summary-private.json').read_text()) if (root/'summary-private.json').exists() else None,
 failure=(root/'failure-private.txt').read_text() if (root/'failure-private.txt').exists() else None)))
'''
q=host.ssh('python3 -',input=('identity='+repr(identity)+'\n'+code).encode(),timeout=20)
report=json.loads(q.stdout);(host.PRIVATE/'calibration-hold-poll-private.json').write_bytes(q.stdout)
if report['summary']:(ROOT/'eeprom-read-validation.json').write_text(json.dumps({k:v for k,v in report['summary'].items() if k!='reads'},indent=2)+'\n')
summary=report['summary']
print(json.dumps(dict(state=report['state'],matching_worker_live=report['matching_worker_live'],failure=report['failure'],summary=None if summary is None else {k:summary[k] for k in ['tool_exit','actual_frames','statistics_frames','passed','graph_restored','fault_delta']}),indent=2))
