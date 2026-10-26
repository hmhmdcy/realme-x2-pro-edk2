"""Audit actual GTM receipts, same-SOF PD10, IPE programs and final history."""
from pathlib import Path
import json,re,sys
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;attempt=sys.argv[1] if len(sys.argv)>1 else 'r3';root=P/('runtime-collected-'+attempt);state=json.loads((root/'state.json').read_text())
assert state['terminal'] and state['passed'] and state['formal_modules_restored'] and state['services_restored'] and not state['new_faults'] and state['taint_before']==state['taint_after']==0
s=state['candidate_final_status'];assert s['jobs']==s['completed']==s['direct_completed']
assert not any(s[k] for k in ['users','running','failed','cancelled','first_error','fatal','pinned','orphans'])
rows=[];all_images=all_math=all_bootstrap=0
for name,summary in state['captures'].items():
 text=(root/name/'client.log').read_text();assert 'IMAGE_PAIR_TIMEOUT' not in text and 'IPE_TONE_REJECT' not in text and 'IFE_GTM_REJECT' not in text and 'Rejected AE update' not in text
 observations={};by_sof={};versions={};applied={};prepares={};queues={};receipts={};pd10=set();bootstrap={};frames=[];last_sof=None;revision=0;pending=None;previous_lux=0
 lines=text.splitlines()
 for line in lines:
  v=dict(re.findall(r'([a-z][a-z0-9-]*)=([^ ]+)',line))
  if 'IFE_GTM_QUEUE ' in line:
   cookie=int(v['cookie']);assert cookie not in versions;versions[cookie]=v
  if 'IFE_GTM_APPLIED ' in line:
   cookie=int(v['cookie']);assert cookie not in applied and cookie in versions
   q=versions[cookie];assert all(v[k]==q[k] for k in ['revision','source-sof','source-histogram','ready']);assert int(v['generation'])==len(applied)+1;applied[cookie]=v
  if 'PD10_READY ' in line:assert v['bytes']=='46080';pd10.add(int(v['sof']))
  if 'IPE_OBSERVE ' in line:
   token=int(v['token']);assert token not in observations;observations[token]=v;by_sof[int(v['sof'])]=v
  if 'IPE_TONE_BOOTSTRAP ' in line:bootstrap[int(v['sof'])]=v
  if 'IPE_TONE_PREPARE ' in line:
   token=int(v['token']);sof=int(v['sof']);cookie=int(v['gtm-cookie']);obs=observations[token];q=versions[cookie];ack=applied[cookie]
   assert pending is None and int(v['base'])==revision and int(v['revision'])==revision+1
   assert v['sof']==obs['sof'] and v['histogram']==obs['trace'] and v['gtm-cookie']==obs['gtm-cookie'] and v['gtm-generation']==obs['gtm-generation']==ack['generation']
   assert q['ready']==q['enabled']=='1' and v['gtm-source-sof']==q['source-sof'] and int(q['source-sof'])<sof and int(ack['sof'])<=sof
   source=by_sof[int(q['source-sof'])];assert q['source-histogram']==source['trace']==v['gtm-source-histogram']
   assert float(v['previous-ltm-lux'])==previous_lux and obs['lux-valid']==obs['gamma-override']=='1'
   prepares[token]=v;pending=token
  if 'IPE_TONE_QUEUE ' in line:
   token=int(v['token']);sof=int(v['sof']);assert token not in queues and v['pd10']=='1' and v['result']=='0' and sof in pd10
   assert last_sof is None or sof>last_sof;last_sof=sof;queues[token]=v
   if v['fresh']=='1':assert token==pending and v['revision']==prepares[token]['revision']
   else:assert sof in bootstrap and int(bootstrap[sof]['cookie'])==int(observations[token]['gtm-cookie'])
  if 'IPE_TONE_RECEIPT ' in line:
   token=int(v['token']);assert token==pending and token in queues and v['result']==v['success']=='1'
   p=prepares[token];assert v['gtm-cookie']==p['gtm-cookie'] and v['gtm-generation']==p['gtm-generation'];revision+=1;assert int(v['revision'])==revision
   previous_lux=float(p['lux']);pending=None;receipts[token]=v
  if 'IPE_TONE_STOP ' in line:assert int(v['revision'])==revision and v['pending']=='0'
  if 'ADAPT_FRAME ' in line:frames.append(v)
 assert pending is None and set(receipts)==set(prepares) and len(frames)==len(queues)==summary['frames']==24
 for frame in frames:
  sof=int(frame['sequence']);assert sof in pd10
  token=int(by_sof[sof]['token']);assert token in queues
  raw=(root/name/('frame-'+str(sof)+'.nv12')).read_bytes();assert len(raw)==460800 and abs(sum(raw[:307200])/307200-float(frame['mean-y']))<.00001
 assert len(bootstrap)+revision==24 and revision>0 and len(applied)>1
 app=set(re.findall(r'ADAPT_PID value=(\d+)',text));ipa=set(re.findall(r'IPA stats pid=(\d+)',text));assert len(app)==len(ipa)==1
 assert bool(app&ipa)==(name=='scene-native')
 row=dict(capture=name,frames=24,real_same_sof_pd10_ipe_jobs=24,gtm_versions_queued=len(versions),gtm_versions_observed=len(applied),gtm_banks_observed=sorted({int(v['bank']) for v in applied.values()}),numeric_history_commits=revision,explicit_bootstrap_frames=len(bootstrap),actual_gtm_cookie_generation_bound_to_successful_history=True,source_statistics_precede_applied_image=True,ipe_queue_sofs_strictly_increasing=True,previous_ltm_lux_from_successful_history=True,isolated=name.endswith('isolated'),passed=True)
 rows.append(row);all_images+=24;all_math+=revision;all_bootstrap+=len(bootstrap)
 images=sorted((root/name).glob('*.nv12'),key=lambda p:int(p.stem.split('-')[1]));sys.path.insert(0,str(HERE.parent/'kernel423'));from nv12 import render
 render(images[-1].read_bytes(),P/(name+'-last-private.png'));render(images[0].read_bytes(),P/(name+'-first-private.png'))
assert s['completed']==all_images==48
kernel=(root/'kernel-log-private.txt').read_text()
assert kernel.count('A5 IPE create acknowledged type=2')==4
assert kernel.count('A5 IPE CONFIG_IO acknowledged scratch=48')==2 and kernel.count('A5 IPE CONFIG_IO acknowledged scratch=46128')==2
assert kernel.count('A5 IPE frame completed request=')==48
failures=[]
for failed,cause in [('r1','Waiting FULL lost PD10 to stale eviction; later image bypassed it'),('r2','Requested controls waited for GTM receipt while blocking statistics needed for that receipt')]:
 old=json.loads((P/('runtime-collected-'+failed)/'state.json').read_text());assert old['terminal'] and not old['passed'] and old['formal_modules_restored'] and old['services_restored'] and not old['new_faults'] and old['taint_after']==0
 failures.append(dict(attempt=failed,acceptance_passed=False,reported_frames=old['captures']['scene-native']['frames'],tone_prepares=old['captures']['scene-native']['tone_prepares'],cause=cause,formal_environment_restored=True,new_faults=0,taint=0))
r=dict(stage=435,scope='Main S5KGW1 4608x3456 single-exposure linear AE/AWB; FULL640x480 plus native PD10160x120; original TMC11 model2/GTM and IPE LTM; ordinary and isolated IPA5',userspace_build=json.loads((HERE/'build-validation.json').read_text())['attempt'],kernel_candidate_stage=434,rows=rows,live_images=all_images,automatic_pd10_ipe_jobs=all_images,automatic_gtm_tmc_ltm_dual_pass_jobs=all_math,successful_numeric_history_commits=all_math,explicit_bootstrap_without_numeric_commit=all_bootstrap,actual_rt_type2_and_bootstrap_to_dc_context_transition_each_stream=True,
 typed_gtm_actual_receipt_controls_parameter_context=True,applied_version_same_sof_pd10_ipe_and_final_success_history_verified=True,original_gtm_share_preserved=True,internal_dc_average_sram_dump=False,full_factory_pipeline_complete=False,absolute_image_quality_accepted=False,
 accepted_attempt=attempt,earlier_attempts=failures,
 scene_pngs_visually_reviewed=(attempt=='r3'),image_issues=['hazy/washed-out appearance','green cast','ring-like luminance gradients'] if attempt=='r3' else [],formal_modules_services_resources_restored=True,new_faults=0,taint_after=0,installed=False,passed=True)
(HERE/'hardware-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
