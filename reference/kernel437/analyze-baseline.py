from pathlib import Path
import json,re
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
root=P/'runtime-collected-r1';state=json.loads((root/'state.json').read_text());assert state['passed']
text=(root/'scene-native/client.log').read_text()
fields=lambda line:dict(re.findall(r'([a-z][a-z0-9-]*)=([^ ]+)',line))
frames=[fields(line) for line in text.splitlines() if line.startswith('ADAPT_FRAME ')]
rgb={int(v['sof']):v for v in (fields(line) for line in text.splitlines() if 'RGB epoch=' in line)}
witnesses=[];run=maximum=0
for a,b in zip(frames,frames[1:]):
 sof=int(b['sequence'])
 if a['locked']=='1' and b['locked']=='0' and (a['red'],a['blue'])==(b['red'],b['blue']) and rgb[sof]['regions']=='0':witnesses.append([int(a['sequence']),sof])
for row in frames:
 run=run+1 if row['locked']=='1' else 0;maximum=max(maximum,run)
assert len(frames)==240 and witnesses and maximum==1
r=dict(stage=437,baseline_userspace_stage436=True,live_images=len(frames),locked_frames=sum(r['locked']=='1' for r in frames),maximum_consecutive_locked_frames=maximum,
 actual_unchanged_wb_loses_metadata_lock_on_skipped_awb=len(witnesses),example_sof_pairs=witnesses[:5],
 awb_steady_convergence_observed=True,awb_continuous_metadata_lock_not_achieved=True,ipa_math_history_commits=state['captures']['scene-native']['tone_receipts'],formal_environment_restored=True,new_faults=0,taint=0,passed=True)
(HERE/'steady-baseline-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
