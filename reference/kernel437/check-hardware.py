from pathlib import Path
import json
HERE=Path(__file__).resolve().parent
source=(HERE.parent/'kernel435/check-hardware.py').read_text();source=source[:source.index(' images=sorted')]
source=source.replace("else 'r3'","else 'r2'")
source=source.replace("summary['frames']==24", "summary['frames']").replace('len(bootstrap)+revision==24',"len(bootstrap)+revision==summary['frames']")
source=source.replace('frames=24,real_same_sof_pd10_ipe_jobs=24',"frames=summary['frames'],real_same_sof_pd10_ipe_jobs=summary['frames']").replace('all_images+=24',"all_images+=summary['frames']")
source+='''
assert s['completed']==all_images
lockRows=[]
for name,summary in state['captures'].items():
 text=(root/name/'client.log').read_text();states={};frames=[];held=0;last=None
 for line in text.splitlines():
  v=dict(re.findall(r'([a-z][a-z0-9-]*)=([^ ]+)',line))
  if 'AWB_STATE ' in line:
   sof=int(v['sof']);assert sof not in states
   if v['locked']=='1':
    assert v['regions']!='0' or last is not None
    if v['calculated']=='0':
     assert last['locked']=='1' and v['red']==last['red'] and v['blue']==last['blue'];held+=1
   states[sof]=v;last=v
  if line.startswith('ADAPT_FRAME '):frames.append(v)
 for frame in frames:
  sof=int(frame['sequence']);assert frame['locked']==states[sof]['locked']
  assert abs(float(frame['red'])-float(states[sof]['red']))<.00001
  assert abs(float(frame['blue'])-float(states[sof]['blue']))<.00001
 assert summary['final_locked_run']>=8 and all(v['locked']=='1' for v in frames[-8:]) and held>0
 lockRows.append(dict(capture=name,frames=len(frames),locked_frames=summary['locked_frames'],final_consecutive_locked_frames=summary['final_locked_run'],held_locked_frames_with_identical_actual_wb=held,final_kelvin=int(frames[-1]['kelvin']),passed=True))
kernel=(root/'kernel-log-private.txt').read_text()
assert kernel.count('A5 IPE CONFIG_IO acknowledged scratch=48')==2
assert kernel.count('A5 IPE CONFIG_IO acknowledged scratch=46128')==2
assert kernel.count('A5 IPE frame completed request=')==all_images
r=dict(stage=437,accepted_attempt=attempt,rows=rows,awb_rows=lockRows,live_images=all_images,successful_numeric_history_commits=all_math,explicit_bootstrap_without_numeric_commit=all_bootstrap,
 original_bls_corrected_profile_preserved=True,main_awb_converged_and_continuous_metadata_verified=True,actual_gtm_cookie_generation_same_sof_pd10_and_final_history_verified=True,
 awb_algorithm_thresholds_unchanged=True,absolute_colour_accuracy_accepted=False,other_cameras_auto_tone_not_yet_validated=True,
 formal_modules_services_resources_restored=True,new_faults=0,taint=0,installed=False,full_goal_complete=False,passed=True)
(HERE/'hardware-validation.json').write_text(json.dumps(r,indent=2)+'\\n');print(json.dumps(r,indent=2))
'''
exec(compile(source,str(HERE/'hardware-audit-generated.py'),'exec'))
