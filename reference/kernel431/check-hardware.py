"""Audit same-SOF PD10, actual dynamic programs, and final math receipts."""
from pathlib import Path
import hashlib,json,re,sys
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;root=P/'runtime-collected-r4';s=json.loads((root/'state.json').read_text())
assert s['terminal'] and s['passed'] and s['formal_modules_restored'] and s['services_restored'] and not s['new_faults'] and s['taint_before']==s['taint_after']==0
status=s['candidate_final_status'];assert status['jobs']==status['completed']==status['direct_completed']==52 and not any(status[k] for k in ['failed','cancelled','first_error','fatal','pinned','orphans','users','running'])
for a,b in [(0,2),(1,3)]:assert (root/f'transition/mode-{a}-output-private.bin').read_bytes()==(root/f'transition/mode-{b}-output-private.bin').read_bytes()
assert (root/'transition/mode-1-output-private.bin').read_bytes()==(P.parent/'kernel430/runtime-collected-r2/replay/mode-0-output-private.bin').read_bytes()
rows=[]
for name,summary in s['captures'].items():
 text=(root/name/'client.log').read_text();observations={};prepares={};pd10=set();queued=set();commits=set();revision=0;pending=None;lastLux=0;meta=[];traces=set()
 assert 'IMAGE_PAIR_TIMEOUT' not in text and 'Rejected AE update' not in text and 'pd10=1' in text
 for line in text.splitlines():
  v=dict(re.findall(r'([a-z][a-z0-9-]*)=([^ ]+)',line))
  if 'PD10_READY ' in line:assert v['bytes']=='46080';pd10.add(int(v['sof']))
  if 'IPE_OBSERVE ' in line:observations[int(v['token'])]=v
  if 'IPE_TONE_PREPARE ' in line:
   token=int(v['token']);assert pending is None and int(v['base'])==revision and int(v['revision'])==revision+1
   obs=observations[token];assert v['sof']==obs['sof'] and v['histogram']==obs['trace'] and obs['lux-valid']==obs['gamma-override']=='1'
   assert float(v['previous-ltm-lux'])==lastLux and v['bytes']=='6008';pending=token;prepares[token]=v;traces.add(v['trace'])
  if 'IPE_TONE_QUEUE ' in line:
   assert v['pd10']=='1' and v['result']=='0' and int(v['sof']) in pd10
   if v['fresh']=='1':
    token=int(v['token']);assert token==pending and v['sof']==prepares[token]['sof'] and v['revision']==prepares[token]['revision'];queued.add(token)
  if 'IPE_TONE_RECEIPT ' in line:
   token=int(v['token']);assert token==pending and token in queued and token not in commits and v['result']==v['success']=='1'
   revision+=1;assert int(v['revision'])==revision;lastLux=float(prepares[token]['lux']);pending=None;commits.add(token)
  if 'IPE_TONE_STOP ' in line:assert int(v['revision'])==revision and v['pending']=='0'
  if 'ADAPT_FRAME ' in line:meta.append(v)
 assert revision==24 and queued==commits==set(prepares) and len(meta)==summary['frames']==24
 images=list((root/name).glob('*.nv12'));assert len(images)==24
 for v in meta:
  raw=(root/name/('frame-'+v['sequence']+'.nv12')).read_bytes();assert len(raw)==460800
  assert int(v['sequence']) in pd10 and abs(sum(raw[:307200])/307200-float(v['mean-y']))<0.00001
  assert int(v['exposure'])>0 and float(v['gain'])>0
 app=set(re.findall(r'ADAPT_PID value=(\d+)',text));ipa=set(re.findall(r'IPA stats pid=(\d+)',text));assert len(app)==1 and len(ipa)==1
 assert bool(app&ipa)==(name=='scene-native')
 rows.append(dict(capture=name,frames=24,real_same_sof_pd10_queued=24,numeric_commits=24,unique_parameter_traces=len(traces),exposure_changes=len({(v['exposure'],v['gain']) for v in meta})-1,
  previous_ltm_lux_equals_previous_successful_commit=True,final_revision=revision,isolated=name.endswith('isolated'),passed=True))
kernel=(root/'kernel-log-private.txt').read_text();assert 'A5 IPE create acknowledged type=2' in kernel and 'CONFIG_IO acknowledged scratch=46128' in kernel and 'CONFIG_IO acknowledged scratch=48' in kernel
failed=[]
for attempt in ['r1','r2','r3']:
 old=json.loads((P/f'runtime-collected-{attempt}/state.json').read_text());assert old['terminal'] and not old['passed'] and old['formal_modules_restored'] and old['services_restored'] and old['taint_after']==0
 failed.append(dict(attempt=attempt,acceptance_passed=False,formal_environment_restored=True,taint=0))
r=dict(stage=431,scope='Main4608x3456 sensor, FULL640x480 and native160x120 PD10, single-exposure linear AE/AWB; stock tuning, ordinary and isolated IPA4',
 kernel_commit=json.loads((HERE/'kernel-source-state.json').read_text())['commit'],userspace_build=7,matched_intree_build=1,
 rows=rows,live_images=48,automatic_dual_pass_jobs=48,numeric_history_commits=48,total_direct_jobs_in_successful_attempt=52,
 bypass_dc_bypass_dc_persistent_session_transition_jobs=4,bypass_repeat_equal=True,dc_repeat_equal=True,dc_output_equals430_reference=True,
 actual_rt_handle2_observed_in_kernel_log=True,original_dc_bank0_reset_then_ip_policy_verified_by_native_instructions=True,
 same_sof_pd10_to_actual_program_to_successful_history_receipt_verified=True,
 internal_average_sram_byte_dump=False,gtm_applied_version_history_association_complete=False,full_factory_pipeline_complete=False,
 earlier_integration_failures=failed,formal_modules_services_resources_restored=True,new_faults=0,taint_after=0,installed=False,absolute_image_quality_calibration_accepted=False,passed=True)
(HERE/'hardware-validation.json').write_text(json.dumps(r,indent=2)+'\n')
sys.path.insert(0,str(HERE.parent/'kernel423'));from nv12 import render
for name in s['captures']:
 images=sorted((root/name).glob('*.nv12'),key=lambda p:int(p.stem.split('-')[1]));render(images[-1].read_bytes(),P/(name+'-last-private.png'))
print(json.dumps(r,indent=2))
