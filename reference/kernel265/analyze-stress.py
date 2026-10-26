from pathlib import Path
import json
import host
R=Path(__file__).parent
code=r'''
from pathlib import Path
import json,re
p=Path('/var/lib/samurai/k265-camera-6');d=json.loads((p/'summary.json').read_text());assert json.loads((p/'state-private.json').read_text())['state']=='terminal'
s=(p/'stderr-private.txt').read_text(errors='replace');lines=s.splitlines();events=[]
for i,l in enumerate(lines):
 if 'was not recycled' in l:
  events.append(dict(line=i,context=lines[max(0,i-18):i+5]))
logs={}
for name in ['pipewire','wireplumber']:
 f=p/(name+'-trace-private.log');t=f.read_text(errors='replace');ls=t.splitlines()
 logs[name]=dict(bytes=f.stat().st_size,lines=len(ls),tee_reuse_count=t.count('tee reuse buffer'),busy_summary=[l for l in ls if 'busy-ownership' in l],camera_starts=[l for l in ls if 'starting camera' in l],camera_stops=[l for l in ls if 'stopping camera' in l],mix_rebinds=[l for l in ls if 'reset camera mix' in l],reuse_tail=[l for l in ls if 'tee reuse buffer' in l][-12:])
result=dict(stage=265,run=6,held_checked=d['probe_result']['held_checked'],held_changes=d['probe_result']['held_change_details'],shots=d['probe_result'].get('shots'),runtime_logging_restored=d['runtime_logging_restored'],recycle_errors=len(events),events=events,logs=logs)
print(json.dumps(result,indent=2))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=25);(host.PRIVATE/'stress-analysis-private.json').write_bytes(q.stdout);print(q.stdout.decode())
