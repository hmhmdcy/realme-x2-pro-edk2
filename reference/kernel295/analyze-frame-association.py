"""Compare reported parameter sequence with observed hardware color changes."""
from pathlib import Path
import json,re
ROOT=Path(__file__).resolve().parent
capture=json.loads((ROOT/'stats-capture-validation.json').read_text());pixels=json.loads((ROOT/'stats-pixel-validation.json').read_text())
text=capture['tool_output'];frames=[];completions=[]
for line in text.splitlines():
 if line.startswith('PIX_LEVEL '):
  d=dict(re.findall(r'(\w+)=([\d.]+)',line));frames.append({k:(float(v) if k.endswith('_y') else int(v)) for k,v in d.items()})
 if line.startswith('PARAM_DQ '):completions.append({k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',line)})
indices=[0,5,3,6];fields=['white_y','red_y','green_y','blue_y'];rows=[]
for event in completions:
 phase=event['phase'];expected=[pixels['phases'][phase]['patches'][i]['expected_yuv'][0] for i in indices]
 phaseframes=[f for f in frames if f['phase']==phase]
 matches=[f for f in phaseframes if max(abs(f[k]-v) for k,v in zip(fields,expected))<=4]
 first=matches[0] if matches else None
 first_index=phaseframes.index(first) if first else None
 late_stable=bool(first) and all(max(abs(f[k]-v) for k,v in zip(fields,expected))<=4 for f in phaseframes[first_index:])
 rows.append(dict(phase=phase,parameter_reported_sequence=event['sequence'],first_observed_matching_sequence=first['sequence'] if first else None,
  observed_minus_reported=first['sequence']-event['sequence'] if first else None,phase_late_frame_matches=bool(matches),
  matching_state_stable_to_phase_end=late_stable,
  note='Unchanged unity phases cannot prove the first affected frame' if phase in [0,5] else 'Color transition observed through captured buffer sequence'))
report=dict(stage=295,frames=len(frames),parameter_completions=len(completions),transitions=rows,
 exact_frame_association_proven=all(r['observed_minus_reported']==0 and r['matching_state_stable_to_phase_end'] for r in rows if r['phase'] in [1,2,3,4,6]),
 measurement_scope='Single queued parameter, physical S5K3M5 color pattern, FULL 320x240 NV12; not request API integration')
(ROOT/'frame-association-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
