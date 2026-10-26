"""Audit real front PD10, effective GTM/WB, IPE colour and final history."""
from pathlib import Path
import hashlib,json,re,struct,sys
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;attempt=sys.argv[1] if len(sys.argv)>1 else 'r1';root=P/('runtime-collected-'+attempt);state=json.loads((root/'state.json').read_text())
assert state['passed'] and state['terminal'] and state['formal_modules_restored'] and state['services_restored']
assert not state['new_faults'] and state['taint_before']==state['taint_after']==0
s=state['candidate_final_status'];assert s['jobs']==s['completed']==s['direct_completed'] and not any(s[k] for k in ['users','running','failed','cancelled','first_error','fatal','pinned','orphans'])
rows=[];all_images=all_math=all_bootstrap=all_discarded=0
for name,summary in state['captures'].items():
 text=(root/name/'client.log').read_text();assert all(x not in text for x in ['IMAGE_PAIR_TIMEOUT','IPE_TONE_REJECT','IFE_GTM_REJECT','Rejected AE update'])
 observations={};by_sof={};versions={};applied={};prepares={};queues={};receipts={};pd10=set();bootstrap={};frames=[];ccms={};awb={};discarded=set();stopping=False;revision=0;pending=None;previous_lux=0;last_sof=None;last_awb=None;held_locked=0
 for line in text.splitlines():
  v=dict(re.findall(r'([a-z][a-z0-9-]*)=([^ ]+)',line))
  if line.startswith('ADAPT_PHASE '):stopping=True
  if 'IFE_GTM_QUEUE ' in line:
   cookie=int(v['cookie']);assert cookie not in versions and v['enabled']=='0';versions[cookie]=v
  if 'IFE_GTM_APPLIED ' in line:
   cookie=int(v['cookie']);assert cookie not in applied and cookie in versions
   q=versions[cookie];assert all(v[k]==q[k] for k in ['revision','source-sof','source-histogram','ready']);assert int(v['generation'])==len(applied)+1;applied[cookie]=v
  if 'PD10_READY ' in line:assert v['bytes']=='46080';pd10.add(int(v['sof']))
  if 'IPE_OBSERVE ' in line:
   token=int(v['token']);assert token not in observations;observations[token]=v;by_sof[int(v['sof'])]=v
  if 'IPE_TONE_BOOTSTRAP ' in line:
   assert v['ccm']=='1';bootstrap[int(v['sof'])]=v
  if 'IPE_TONE_PREPARE ' in line:
   token=int(v['token']);sof=int(v['sof']);cookie=int(v['gtm-cookie']);obs=observations[token];q=versions[cookie];ack=applied[cookie]
   assert pending is None and int(v['base'])==revision and int(v['revision'])==revision+1
   assert v['sof']==obs['sof'] and v['histogram']==obs['trace'] and v['gtm-cookie']==obs['gtm-cookie'] and v['gtm-generation']==obs['gtm-generation']==ack['generation']
   assert q['ready']=='1' and q['enabled']=='0' and v['gtm-source-sof']==q['source-sof'] and int(q['source-sof'])<sof and int(ack['sof'])<=sof
   source=by_sof[int(q['source-sof'])];assert q['source-histogram']==source['trace']==v['gtm-source-histogram']
   assert float(v['previous-ltm-lux'])==previous_lux and obs['lux-valid']==obs['gamma-override']=='1'
   prepares[token]=v;pending=token
  if 'IPE_CCM_PREPARE ' in line:
   token=int(v['token']);obs=observations[token];assert token not in ccms and v['sof']==v['source-sof']==obs['sof'] and v['isp-revision']==obs['revision'] and v['manual']=='0' and v['qfactor']=='0';ccms[token]=v
  if 'IPE_TONE_QUEUE ' in line:
   token=int(v['token']);sof=int(v['sof']);assert token not in queues and v['pd10']=='1' and v['result']=='0' and sof in pd10
   assert last_sof is None or sof>last_sof;last_sof=sof;queues[token]=v
   if v['fresh']=='1':assert token==pending and v['revision']==prepares[token]['revision']
   else:assert sof in bootstrap and int(bootstrap[sof]['cookie'])==int(observations[token]['gtm-cookie'])
  if 'IPE_TONE_RECEIPT ' in line:
   token=int(v['token']);assert token==pending
   p=prepares[token];assert v['gtm-cookie']==p['gtm-cookie'] and v['gtm-generation']==p['gtm-generation']
   if v['success']=='1':
    assert v['result']=='1' and token in queues;revision+=1;previous_lux=float(p['lux']);receipts[token]=v
   else:
    assert stopping and v['success']==v['result']=='0';discarded.add(token)
   assert int(v['revision'])==revision;pending=None
  if 'IPE_TONE_STOP ' in line:assert int(v['revision'])==revision and v['pending']=='0'
  if 'AWB_STATE ' in line:
   sof=int(v['sof']);assert sof not in awb
   if v['locked']=='1' and v['calculated']=='0':
    assert last_awb and last_awb['locked']=='1' and v['red']==last_awb['red'] and v['blue']==last_awb['blue'];held_locked+=1
   awb[sof]=v;last_awb=v
  if line.startswith('ADAPT_FRAME '):frames.append(v)
 assert pending is None and set(receipts)|discarded==set(prepares)==set(ccms)
 assert len(frames)==len(queues)==summary['frames'] and len(bootstrap)+revision==len(frames)
 for frame in frames:
  sof=int(frame['sequence']);token=int(by_sof[sof]['token']);assert token in queues and token not in discarded and sof in pd10
  if token in ccms:assert frame['kelvin']==ccms[token]['cct']
  assert frame['locked']==awb[sof]['locked']
  assert abs(float(frame['red'])-float(awb[sof]['red']))<.00001 and abs(float(frame['blue'])-float(awb[sof]['blue']))<.00001
  matrix=list(map(float,frame['matrix'].split(',')));assert len(matrix)==9 and any(abs(x-y)>1e-4 for x,y in zip(matrix,[1,0,0,0,1,0,0,0,1]))
  assert all(abs(v*128-round(v*128))<.001 and -2048<=round(v*128)<=2047 for v in matrix)
  raw=(root/name/f'frame-{sof}.nv12').read_bytes();assert len(raw)==460800 and abs(sum(raw[:307200])/307200-float(frame['mean-y']))<.00001
 assert summary['final_locked_run']>=8 and all(v['locked']=='1' for v in frames[-8:]) and held_locked>0
 app=set(re.findall(r'ADAPT_PID value=(\d+)',text));ipa=set(re.findall(r'IPA stats pid=(\d+)',text));assert len(app)==len(ipa)==1 and bool(app&ipa)==(name=='scene-native')
 trace=summary['trace'];sof=trace['sof'];packet=(root/name/f'tone-{sof}-params.bin').read_bytes();assert len(packet)==6008 and struct.unpack_from('<4I',packet)==(1,6008,3,0) and struct.unpack_from('<I',packet,32)[0]==7
 # Colour starts at32; module flags4B, CST42B, padding2B; CC starts at80.
 coeff=struct.unpack_from('<9h',packet,80);q=struct.unpack_from('<I',packet,104)[0];assert q==0
 metadata=next(f for f in frames if int(f['sequence'])==sof);assert tuple(round(float(v)*128) for v in metadata['matrix'].split(','))==coeff
 assert trace['full_kernel_sequence']==trace['pd10_kernel_sequence']
 rows.append({'capture':name,'delivered_images':len(frames),'successful_numeric_commits':revision,'explicit_bootstrap_images':len(bootstrap),'discarded_stop_proposals':len(discarded),'same_sof_pd10_and_colour_metadata':True,'gtm_original_disabled_versions_observed':len(applied),'gtm_banks':sorted({int(v['bank']) for v in applied.values()}),'final_locked_run':summary['final_locked_run'],'held_locked_same_wb_frames':held_locked,'trace_packet_matches_applied_matrix_metadata':True,'passed':True})
 all_images+=len(frames);all_math+=revision;all_bootstrap+=len(bootstrap);all_discarded+=len(discarded)
replay=state['replay'];assert all(replay[k] for k in ['stock_repeat_equal','stock_matches_live','ltm_changes_pixels','ipe_ccm_changes_pixels']) and replay['frames']==5
assert s['completed']==all_images+5
native=root/'scene-native';sof=replay['source_sof'];rdir=root/'replay';outputs=[(rdir/f'mode-{i}-output-private.bin').read_bytes() for i in range(5)]
assert outputs[0]==outputs[4]==(native/f'frame-{sof}.nv12').read_bytes() and outputs[0]!=outputs[1] and outputs[0]!=outputs[2]
for src,dst in [(f'tone-{sof}-full.nv12','full-private.bin'),(f'tone-{sof}-coarse.pd10','pd10-private.bin'),(f'tone-{sof}-params.bin','parameters-private.bin')]:assert (native/src).read_bytes()==(rdir/dst).read_bytes()
kernel=(root/'kernel-log-private.txt').read_text();assert kernel.count('A5 IPE frame completed request=')==all_images+5
r={'stage':439,'accepted_attempt':attempt,'rows':rows,'live_delivered_images':all_images,'successful_numeric_history_commits':all_math,'explicit_bootstrap_without_math_commit':all_bootstrap,'stop_proposals_discarded_without_commit':all_discarded,'fixed_input_hardware_replays':5,'stock_repeat_and_live_byte_identical':True,'original_ltm_and_ipe_ccm_change_pixels':True,'actual_gtm_cookie_generation_same_sof_pd10_colour_final_history_verified':True,'original_front_tmc_gtm_disabled_preserved':True,'formal_modules_services_resources_restored':True,'new_faults':0,'taint':0,'installed':False,'absolute_image_quality_accepted':False,'full_goal_complete':False,'passed':True}
(HERE/'hardware-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
