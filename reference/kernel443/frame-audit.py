"""Retain strict pipeline history audit, using real GST offsets as consumer SOF.

GStreamer may have already accepted buffers that appsink has not pulled at stop.
Keep those source receipts distinct from the 120 consumed samples. No application
AWB metadata or lock-policy assertions are fabricated for this consumer API.
"""
from pathlib import Path
import importlib.util,re
spec=importlib.util.spec_from_file_location('frame441',Path(__file__).resolve().parents[1]/'kernel441/frame-audit.py')
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old);source=old._source
def replace(a,b):
 global source
 assert source.count(a)==1,(a,source.count(a));source=source.replace(a,b)
replace('def audit_auto(', 'def audit_gst(')
replace(' observations={};', " assert model=='s5kgw1' and folder is None\n wb_contexts={};observations={};")
replace("  if line.startswith('ADAPT_PHASE '):stopping=True", "  if 'REQUEST_STOP_CANCEL ' in line:stopping=True\n  if 'WB context epoch=' in line:\n   sof=int(v['sof']);assert v['known']=='1' and sof not in wb_contexts;wb_contexts[sof]=v")
replace("  if line.startswith('ADAPT_FRAME '):frames.append(v)", "  if line.startswith('GST_IMAGE '):frames.append(v)")
replace(' assert len(frames)==len(bootstrap)+revision and revision>0', " all_success={t for t,v in observation_receipts.items() if v['success']=='1'}\n assert len(all_success)==len(bootstrap)+revision and revision>0")
start=source.index("  assert frame['locked']==awb[sof]['locked']")
end=source.index('  if folder is not None:',start)
source=source[:start]+"  assert sof in awb and sof in wb_contexts and wb_contexts[sof]['revision']==obs['revision']==awb[sof]['revision']\n"+source[end:]
replace(" assert all(v['locked']=='1' for v in frames[-8:]) and len(frames)>=24 and held>0", ' assert len(frames)==120')
replace('assert set(queues)==delivered|aborted_queued', 'assert set(queues)==all_success|aborted_queued')
replace("history['committed']==len(frames)", "history['committed']==len(all_success)")
replace('assert resolved_success==delivered', 'assert delivered<=resolved_success')
replace('resolved_failure|stopped_pending==set(observations)-delivered', 'resolved_failure|stopped_pending==set(observations)-resolved_success')
replace('return dict(frames=len(frames),', 'return dict(frames=len(frames),source_delivered_successful_images=len(resolved_success),source_completed_not_pulled=len(resolved_success-delivered),consumer_offsets_match_successful_receipts=True,actual_wb_context_revision_matches_observation=True,')
replace('final_locked_run=8,', "awb_locked_source_frames=sum(v['locked']=='1' for v in awb.values()),")
replace("assert 'failed=0 result=0' in text", "assert 'bus-errors=0 result=0' in text")
exec(compile(source,'retained-441-gst-frame-audit','exec'))
