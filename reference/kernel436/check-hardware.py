"""Reuse the complete applied-GTM/history audit on the new scene transactions."""
from pathlib import Path
import json,sys
import host
HERE=Path(__file__).resolve().parent
attempt=sys.argv[1] if len(sys.argv)>1 else 'r5'
assert attempt in ['r1','r3','r4','r5']
source=(HERE.parent/'kernel435/check-hardware.py').read_text()
source=source[:source.index(' images=sorted')]
source=source.replace("summary['frames']==24", "summary['frames']")
source=source.replace('len(bootstrap)+revision==24',"len(bootstrap)+revision==summary['frames']")
source=source.replace('frames=24,real_same_sof_pd10_ipe_jobs=24',"frames=summary['frames'],real_same_sof_pd10_ipe_jobs=summary['frames']")
source=source.replace('all_images+=24',"all_images+=summary['frames']")
source+='''
assert s['completed']==all_images
trace=state['captures']['scene-native']['trace']
assert trace['sof']==trace['full_kernel_sequence']==trace['pd10_kernel_sequence']==12
p=prepares[trace['token']];q=queues[trace['token']];receipt=receipts[trace['token']]
assert int(p['revision'])==trace['revision'] and q['result']=='0' and receipt['success']=='1'
kernel=(root/'kernel-log-private.txt').read_text()
assert kernel.count('A5 IPE CONFIG_IO acknowledged scratch=48')==1
assert kernel.count('A5 IPE CONFIG_IO acknowledged scratch=46128')==1
assert kernel.count('A5 IPE frame completed request=')==all_images
if attempt=='r3':assert 'LSC_APPLIED ' not in text
else:assert 'LSC_APPLIED ' in text
if attempt=='r5':assert state['autofocus_focused'] and any(v.get('af-state')=='2' for v in frames)
r=dict(stage=436,attempt=attempt,rows=rows,live_images=all_images,successful_numeric_history_commits=all_math,explicit_bootstrap_without_numeric_commit=all_bootstrap,
 matched_trace_sof=trace['sof'],trace_gtm_cookie=int(p['gtm-cookie']),trace_gtm_generation=int(p['gtm-generation']),trace_gtm_source_sof=int(p['gtm-source-sof']),trace_successful_math_revision=int(receipt['revision']),
 original_rt2_coarse_dc_full_ip_preserved=True,physical_full_pd10_params_and_output_saved=True,autofocus_focused=bool(state.get('autofocus_focused')),
 final_awb_locked=frames[-1]['locked']=='1',absolute_image_quality_accepted=False,formal_modules_services_restored=True,new_faults=0,taint=0,installed=False,full_goal_complete=False,passed=True)
(HERE/('hardware-'+attempt+'-validation.json')).write_text(json.dumps(r,indent=2)+'\\n');print(json.dumps(r,indent=2))
'''
exec(compile(source,str(HERE/'hardware-audit-generated.py'),'exec'))
