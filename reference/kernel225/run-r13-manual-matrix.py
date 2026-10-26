"""Reuse only passed receipts; never replay an unresolved native test context."""
from pathlib import Path
import json,subprocess,sys

here=Path(__file__).resolve().parent;results=[]
for profile in ['threaded','isolated']:
 for kind,width,height in [('raw',1928,1088),('raw',2304,1728),('rgb',1920,1088),('rgb',2296,1728)]:
  label=f'r13-{kind}-{width}x{height}-{profile}';receipt=here/(label+'-manual-validation.json')
  if not receipt.exists():subprocess.run([sys.executable,str(here/'run-r13-manual-case.py'),kind,str(width),str(height),profile],check=True,timeout=170)
  r=json.loads(receipt.read_text());assert r['frames']==128 and r['phases']==9 and r['controls_formats_graph_and_pm_restored'] and r['taint']==0
  assert r['captured_source_cookies_and_values_match_metadata'] and r['independent_modes_ae_enable_priority_ignore_freeze_resume_restart_verified']
  assert r['metadata_mode_differs_from_new_request_during_transition_frames']>0
  assert not any(r['fault_delta'].values());results.append(r)
  print(json.dumps(dict(case=label,completed_cases=len(results),verified_frames=sum(x['frames'] for x in results))),flush=True)
r=dict(stage=225,candidate_framework='99990.7.2-r13',cases=results,frames=sum(x['frames'] for x in results),raw_frames=sum(x['frames'] for x in results if '-raw-' in x['case']),
 nine_phase_controls_restart_and_captured_source_verified_in_all_eight_cases=True,threaded_and_isolated_ipa_verified=True,
 system_r11_r6_packages_unchanged=True,no_scene_pixels_mapped_by_client_or_saved=True,physical_optical_delay_not_calibrated=True)
(here/'r13-candidate-manual-matrix-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='cases'}))
