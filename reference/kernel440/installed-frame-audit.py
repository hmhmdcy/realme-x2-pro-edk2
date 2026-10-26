"""Per-SOF audit; extra observed statistics are not delivered images."""
def audit_auto(text,model,folder=None):
 observations={};by_sof={};versions={};applied={};prepares={};queues={};success={};failed=set();pd10=set();bootstrap={};frames=[];ccms={};awb={}
 revision=0;pending=None;previous_lux=0;last_sof=None;last_awb=None;held=0;stopping=False;history=None
 for line in text.splitlines():
  v=dict(re.findall(r'([a-z][a-z0-9-]*)=([^ ]+)',line))
  if line.startswith('ADAPT_PHASE '):stopping=True
  if 'IFE_GTM_QUEUE ' in line:
   cookie=int(v['cookie']);assert cookie not in versions;assert v['enabled']==('1' if model!='imx471' and v['ready']=='1' else '0');versions[cookie]=v
  if 'IFE_GTM_APPLIED ' in line:
   cookie=int(v['cookie']);assert cookie not in applied and cookie in versions;q=versions[cookie]
   assert all(v[k]==q[k] for k in ['revision','source-sof','source-histogram','ready']) and int(v['generation'])==len(applied)+1;applied[cookie]=v
  if 'PD10_READY ' in line:assert v['bytes']=='46080';pd10.add(int(v['sof']))
  if 'IPE_OBSERVE ' in line:
   token=int(v['token']);sof=int(v['sof']);assert token not in observations and sof not in by_sof;observations[token]=v;by_sof[sof]=v
  if 'IPE_TONE_BOOTSTRAP ' in line:
   assert v['ccm']==('1' if model=='imx471' else '0');bootstrap[int(v['sof'])]=v
  if 'IPE_TONE_PREPARE ' in line:
   token=int(v['token']);sof=int(v['sof']);cookie=int(v['gtm-cookie']);obs=observations[token];q=versions[cookie];ack=applied[cookie]
   assert pending is None and int(v['base'])==revision and int(v['revision'])==revision+1
   assert v['sof']==obs['sof'] and v['histogram']==obs['trace'] and v['gtm-cookie']==obs['gtm-cookie'] and v['gtm-generation']==obs['gtm-generation']==ack['generation']
   assert q['ready']=='1' and v['gtm-source-sof']==q['source-sof'] and int(q['source-sof'])<sof and int(ack['sof'])<=sof
   source=by_sof[int(q['source-sof'])];assert q['source-histogram']==source['trace']==v['gtm-source-histogram']
   assert float(v['previous-ltm-lux'])==previous_lux and obs['lux-valid']==obs['gamma-override']=='1'
   assert token not in prepares;prepares[token]=v;pending=token
  if 'IPE_CCM_PREPARE ' in line:
   token=int(v['token']);obs=observations[token];assert model=='imx471' and token not in ccms and v['sof']==v['source-sof']==obs['sof'] and v['isp-revision']==obs['revision'] and v['manual']=='0';ccms[token]=v
  if 'IPE_TONE_QUEUE ' in line:
   token=int(v['token']);sof=int(v['sof']);assert token not in queues and v['pd10']=='1' and v['result']=='0' and sof in pd10 and v['sof']==observations[token]['sof']
   assert last_sof is None or sof>last_sof;last_sof=sof;queues[token]=v
   if v['fresh']=='1':assert token==pending and v['revision']==prepares[token]['revision']
   else:assert sof in bootstrap and bootstrap[sof]['cookie']==observations[token]['gtm-cookie']
  if 'IPE_TONE_RECEIPT ' in line:
   token=int(v['token']);assert token==pending;p=prepares[token]
   assert v['gtm-cookie']==p['gtm-cookie'] and v['gtm-generation']==p['gtm-generation']
   if v['success']=='1':
    assert v['result']=='1' and token in queues;revision+=1;previous_lux=float(p['lux']);success[token]=v
   else:assert stopping and v['success']==v['result']=='0';failed.add(token)
   assert int(v['revision'])==revision;pending=None
  if 'IPE_TONE_STOP ' in line:assert int(v['revision'])==revision and v['pending']=='0'
  if 'IPE_HISTORY_STOP ' in line:assert history is None;history={k:int(v[k]) for k in ['prepared','committed','discarded','superseded','aborted','pending']}
  if 'AWB_STATE ' in line:
   sof=int(v['sof']);assert sof not in awb
   if v['locked']=='1' and v['calculated']=='0':assert last_awb and last_awb['locked']=='1' and v['red']==last_awb['red'] and v['blue']==last_awb['blue'];held+=1
   awb[sof]=v;last_awb=v
  if line.startswith('ADAPT_FRAME '):frames.append(v)
 assert pending is None and set(success)|failed==set(prepares) and set(ccms)==(set(prepares) if model=='imx471' else set())
 assert len(frames)==len(bootstrap)+revision and revision>0
 delivered=set()
 for frame in frames:
  sof=int(frame['sequence']);obs=by_sof[sof];token=int(obs['token']);assert token in queues and token not in failed and sof in pd10 and token not in delivered;delivered.add(token)
  if token in prepares:assert token in success
  if token in ccms:assert frame['kelvin']==ccms[token]['cct']
  assert frame['locked']==awb[sof]['locked'] and abs(float(frame['red'])-float(awb[sof]['red']))<.00001 and abs(float(frame['blue'])-float(awb[sof]['blue']))<.00001
  matrix=list(map(float,frame['matrix'].split(',')));assert len(matrix)==9 and all(abs(v*128-round(v*128))<.001 and -2048<=round(v*128)<=2047 for v in matrix)
  if folder is not None:
   raw=(folder/f'frame-{sof}.nv12').read_bytes();assert len(raw)==460800 and abs(sum(raw[:307200])/307200-float(frame['mean-y']))<.00001
 assert all(v['locked']=='1' for v in frames[-8:]) and len(frames)>=24 and held>0
 aborted_queued=failed & set(queues);unqueued=failed-set(queues)
 assert set(queues)==delivered|aborted_queued and len(aborted_queued)<=1
 assert history and history['committed']==len(frames) and not history['pending'] and not history['superseded']
 assert history['aborted']==len(aborted_queued) and history['prepared']==len(observations)==history['committed']+history['discarded']+history['aborted']
 assert len(set(observations)-set(queues))==history['discarded'] and unqueued<=set(observations)-set(queues)
 assert 'failed=0 result=0' in text and not any(x in text for x in ['IPE_TONE_REJECT','IFE_GTM_REJECT','IMAGE_PAIR_TIMEOUT'])
 return dict(frames=len(frames),successful_math=revision,bootstrap=len(bootstrap),pd10_observed_sofs=len(pd10),discarded_unqueued_observations=history['discarded'],stop_aborted_queued_images=len(aborted_queued),queued_images=len(queues),ccm_domain='IPE' if model=='imx471' else 'IFE',gtm_banks=sorted({int(v['bank']) for v in applied.values()}),held_locked_same_wb_frames=held,final_locked_run=8,same_sof_pd10_gtm_and_successful_history=True,passed=True)
