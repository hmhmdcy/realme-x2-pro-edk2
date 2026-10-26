"""Reuse the installed per-SOF/history audit with explicit image dimensions."""
from pathlib import Path
import re
_source=(Path(__file__).resolve().parents[1]/'kernel440/installed-frame-audit.py').read_text()
def _replace(a,b):
 global _source
 assert _source.count(a)==1,(a,_source.count(a))
 _source=_source.replace(a,b)
_replace('def audit_auto(text,model,folder=None):','def audit_auto(text,model,folder=None,*,width=640,height=480,stride=640,coarse_bytes=46080):')
_replace("v['bytes']=='46080'","int(v['bytes'])==coarse_bytes")
_replace("len(raw)==460800 and abs(sum(raw[:307200])/307200-float(frame['mean-y']))<.00001", "len(raw)==stride*height*3//2 and abs(sum(sum(raw[y*stride:y*stride+width]) for y in range(height))/(width*height)-float(frame['mean-y']))<.00001")
_replace('revision=0;pending=None;', 'observation_receipts={};revision=0;pending=None;')
_replace("  if 'IPE_TONE_STOP ' in line:", """  if 'IPE_RECEIPT ' in line:
   token=int(v['token']);assert token in observations and token not in observation_receipts
   assert v['sof']==observations[token]['sof'] and v['result'] in ['0','1']
   assert v['success']==v['result'];observation_receipts[token]=v
  if 'IPE_TONE_STOP ' in line:""")
_replace("  if token in prepares:assert token in success", "  assert token in observation_receipts and observation_receipts[token]['success']=='1'\n  if token in prepares:assert token in success")
_replace(" assert history['aborted']==len(aborted_queued) and history['prepared']==len(observations)==history['committed']+history['discarded']+history['aborted']\n assert len(set(observations)-set(queues))==history['discarded'] and unqueued<=set(observations)-set(queues)", """ resolved_success={t for t,v in observation_receipts.items() if v['success']=='1'}
 resolved_failure=set(observation_receipts)-resolved_success
 stopped_pending=set(observations)-set(observation_receipts)
 assert resolved_success==delivered
 assert history['discarded']==len(resolved_failure) and history['aborted']==len(stopped_pending)
 assert history['prepared']==len(observations)==history['committed']+history['discarded']+history['aborted']
 assert resolved_failure|stopped_pending==set(observations)-delivered
 assert failed<=resolved_failure|stopped_pending and unqueued<=set(observations)-set(queues)""")
_replace("discarded_unqueued_observations=history['discarded'],", "discarded_unqueued_observations=len(resolved_failure-set(queues)),stop_aborted_unresolved_observations=len(stopped_pending),")
exec(compile(_source,'retained-440-dimension-aware-frame-audit','exec'))
