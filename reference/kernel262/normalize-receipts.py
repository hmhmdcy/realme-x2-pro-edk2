"""Clarify labels inherited from the GUI harness; preserve originals privately."""
from pathlib import Path
import json
import host
R=Path(__file__).parent
def normalize(d):
 if not isinstance(d,dict):return
 if 'application' in d and d['application']=='pipewire-probe':
  if 'gtk_renderer' in d:d['gtk_renderer_requested']=d.pop('gtk_renderer')
  if 'app_still_running_at30s' in d:d['outer_timeout_reached']=d.pop('app_still_running_at30s')
  d.pop('only_this_app_uses_cpu_renderer',None)
  d['gui_window_used']=False
 result=d.get('probe_result')
 if isinstance(result,dict) and result.get('consumer_delay_us',0)>=1000000:
  scenario=result['consumer_delay_us'];result['scenario_code']=scenario
  result['consumer_delay_us']=0
  result['retain_frames_for_ms']=120 if scenario in [1000000,3000000,3000001,4000000] else 0
 if 'consumer_delay_us' in d and 'summary' in d:d['scenario_code']=d.pop('consumer_delay_us')
 if 'summary' in d:normalize(d['summary'])
for p in sorted([*R.glob('probe-*-validation.json'),*R.glob('flow-*-validation.json')]):
 before=p.read_bytes();d=json.loads(before);normalize(d)
 target=host.PRIVATE/(p.stem+'-before-label-review-private.json')
 if not target.exists():target.write_bytes(before)
 p.write_text(json.dumps(d,indent=2)+'\n')
print('Clarified probe metadata; original receipts retained privately.')
