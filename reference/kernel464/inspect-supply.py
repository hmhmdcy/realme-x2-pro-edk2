"""Resolve cached FULL supply intervals and application queue-submit bounds."""
from pathlib import Path
import hashlib,json,re

HERE=Path(__file__).resolve().parent
PRIVATE=Path('/mnt/e/edk2-samurai-out')
root=PRIVATE/'kernel461/runtime-collected-r2'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

# Reuse the validated read-only prefix, without rerunning its report writer.
parser=HERE.parent/'kernel461/inspect-full-gaps.py'
namespace={};source=parser.read_text().split('rows=[];consumed=0')[0]
exec(compile(source,'retained461-full-dq-parser','exec'),namespace)
events=namespace['events'];paired=namespace['paired']
old=json.loads((HERE.parent/'kernel461/full-gap-validation.json').read_bytes())
assert old['passed'] and old['bounded_trace_overrun']==0
client=HERE.parent/'kernel449/lifecycle.cpp'
client_proof=json.loads((HERE.parent/'kernel449/client-build-validation.json').read_bytes())
assert sha(client)==next(row['source_sha256'] for row in client_proof['clients'] if row['name']=='lifecycle')
pipeline=PRIVATE/'kernel461/camss_vfe-candidate.cpp'
source_proof=json.loads((HERE.parent/'kernel461/source-state.json').read_bytes())
assert sha(pipeline)==next(row['sha256'] for row in source_proof['source_hashes'] if row['path']=='src/libcamera/pipeline/camss-vfe/camss_vfe.cpp')
client_source=client.read_text();pipeline_source=pipeline.read_text()
assert 'if (cfg.bufferCount != 4)' in pipeline_source
assert pipeline_source.count('d->image_->queueBuffer(ife)')==1
process=client_source[client_source.index(' void process(Request *request)'):client_source.index('\nint runCycle(')]
assert process.index('meanY(')<process.index('request->reuse(')<process.index('camera->queueRequest(')
completion=pipeline_source[pipeline_source.index('void CamssVfeData::tryComplete('):pipeline_source.index('void CamssVfeData::paramsReady(')]
assert completion.index('freeImages_.push(ife)')<completion.index('handler()->completeBuffer')<completion.index('handler()->completeRequest')

text=(root/'user-native/client.log').read_text()
start=re.search(r'^LIFECYCLE_BEGIN cycle=1 .*$',text,re.M).start()
end=start+re.search(r'^LIFECYCLE_END cycle=1 status=0$',text[start:],re.M).end()
part=text[start:end]
frames=[tuple(map(int,m)) for m in re.findall(r'ADAPT_FRAME phase=\d+ request=(\d+) sequence=(\d+) timestamp=(\d+)',part)]
assert [frame[0] for frame in frames]==list(range(len(frames)))
io={int(sof):dict(enter=int(a),store=int(b),end=int(c)) for sof,a,b,c in re.findall(r'CAPTURE_IO sequence=(\d+) enter=(\d+) store=(\d+) end=(\d+)',part)}
assert len(io)==len(frames)
def stamp(line):
    match=re.match(r'^\[(\d+):(\d+):(\d+)\.(\d+)\]',line)
    assert match
    h,m,s,n=match.groups();return (int(h)*3600+int(m)*60+int(s))*10**9+int(n.ljust(9,'0'))
receipts={};pd10={};focus={}
for line in part.splitlines():
    if not line.startswith('['):continue
    fields=dict(re.findall(r'([a-z][a-z0-9-]*)=([^ ]+)',line))
    if 'IPE_RECEIPT epoch=2 ' in line and fields['success']=='1':receipts[int(fields['sof'])]=stamp(line)
    if 'PD10_READY epoch=2 ' in line:pd10[int(fields['sof'])]=stamp(line)
    if 'FRAME_IPA_PREPARE epoch=2 ' in line:focus[int(fields['sof'])]=dict(focus_us=int(fields['focus-us']),dispatch_us=int(fields['dispatch-us']))
origin=paired[frames[0][2]][0]['ns'];rows=[]
for position,(before,after) in enumerate(zip(frames,frames[1:])):
    if after[1]==before[1]+1:continue
    left,lq=paired[before[2]];right,rq=paired[after[2]]
    assert lq['owner']==rq['owner'] and lq['queued']==lq['owned_by_drv']==0
    owner=lq['owner'];empty_start=lq['ns']
    later=[e for e in events if e.get('owner')==owner and e['ns']>empty_start]
    refill=next(e for e in later if e['kind']=='vb2_qbuf');driver=next(e for e in later if e['kind']=='vb2_buf_queue')
    assert refill['queued']==1 and driver['owned_by_drv']==1 and refill['ns']<=driver['ns']<refill['ns']+100_000
    assert not any(e['kind'] in ['vb2_qbuf','vb2_buf_queue'] for e in later if e['ns']<refill['ns'])
    # Four requests, completed/processed in order. The current single application
    # thread submits the reused request after its image I/O, before the next I/O.
    returning=after[0]-4;original=frames[returning];next_original=frames[returning+1]
    assert returning>=0 and original[0]==returning and original[1] in receipts
    work=io[original[1]];next_work=io[next_original[1]]
    assert receipts[original[1]]<work['enter']<empty_start<work['end']<=next_work['enter']<refill['ns']
    assert paired[original[2]][0]['index']==refill['index']
    duration=(refill['ns']-empty_start)/1e6
    missing=list(range(before[1]+1,after[1]));assert all(sof in pd10 for sof in missing)
    rows.append(dict(after_sof=before[1],before_sof=after[1],missing_sofs=missing,returning_original_request=returning,
        returning_original_sof=original[1],software_queued_zero_duration_ms=round(duration,3),
        software_owned_zero_at_dq=True,application_io_overlap_ms=round((work['end']-empty_start)/1e6,3),
        original_ipe_receipt_before_empty_ms=round((empty_start-receipts[original[1]])/1e6,3),
        application_copy_mean_ms=round((work['store']-work['enter'])/1e6,3),
        application_store_ms=round((work['end']-work['store'])/1e6,3),
        public_queue_submit_bound_width_ms=round((next_work['enter']-work['end'])/1e6,3),
        queue_submit_to_kernel_qbuf_lower_ms=round((refill['ns']-next_work['enter'])/1e6,3),
        queue_submit_to_kernel_qbuf_upper_ms=round((refill['ns']-work['end'])/1e6,3),
        pd10_ready_while_software_queue_empty=any(empty_start<=pd10[sof]<refill['ns'] for sof in missing),
        original_internal_full_returned_before_application_io_by_source_order=True,
        observed_qbuf_index_matches_original_full_index=True,
        original_focus=focus[original[1]],physical_sof_fifo_or_hardware_causality_proven=False))
assert len(rows)==2
report=dict(stage=464,passed=True,cached_camera_window='461-r2',new_phone_or_build_or_sdk_access=False,
    source_client_sha256=sha(client),source_pipeline_sha256=sha(pipeline),reused_trace_parser_sha256=sha(parser),
    matching_four_request_source_and_actual_order_verified=True,receipt_filter_used=False,
    rows=rows,first_three_1080_copy_mean_ms=[round((io[f[1]]['store']-io[f[1]]['enter'])/1e6,3) for f in frames[:3]],
    application_request_supply_interruption_observed=True,driver_held_all_internal_buffers_proven=False,
    prior_450_or_452_gap_same_cause_proven=False,production_isp_tuning_or_buffer_count_changed=False,
    full_camera_goal_complete=False)
(HERE/'supply-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
