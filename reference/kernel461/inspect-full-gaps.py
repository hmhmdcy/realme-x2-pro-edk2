"""Correlate the actual cached FULL ioctl/queue events; no device access."""
from pathlib import Path
import collections,json,re
root=Path('/mnt/e/edk2-samurai-out/kernel461/runtime-collected-r2')
selection=json.loads((root/'selection-private.json').read_bytes())
trace=(root/selection['instance']/'trace-private-1.txt').read_text()
events=[]
for line in trace.splitlines():
    match=re.match(r'^\s*(.*)-(\d+)\s+\[(\d+)\]\s+\S+\s+(\d+\.\d+):\s+(\w+): (.*)$',line)
    if not match:continue
    comm,pid,cpu,stamp,kind,payload=match.groups()
    if kind not in ['v4l2_qbuf','v4l2_dqbuf','vb2_qbuf','vb2_buf_queue','vb2_buf_done','vb2_dqbuf']:continue
    fields=dict(re.findall(r'(owner|queued|owned_by_drv|index|type|bytesused|timestamp|sequence|minor) = ([^,]+)',payload))
    event=dict(kind=kind,pid=int(pid),cpu=int(cpu),ns=round(float(stamp)*1e9),fields=fields)
    for key in ['queued','owned_by_drv','index','bytesused','timestamp','sequence','minor']:
        if key in fields:event[key]=int(fields[key])
    if 'owner' in fields:event['owner']=fields['owner']
    events.append(event)
dq=[e for e in events if e['kind']=='v4l2_dqbuf'];assert len(dq)==286
paired={}
for event in dq:
    matches=[v for v in events if v['kind']=='vb2_dqbuf' and v['pid']==event['pid'] and v['index']==event['index']
        and v['timestamp']//1000*1000==event['timestamp'] and 0<=event['ns']-v['ns']<2_000_000]
    assert len(matches)==1,(event,len(matches))
    paired[event['timestamp']]=(event,matches[0])
assert len(paired)==286
rows=[];consumed=0
for name in ['user-native','user-isolated']:
    text=(root/name/'client.log').read_text()
    starts=list(re.finditer(r'^LIFECYCLE_BEGIN cycle=(\d+) output=(\d+)x(\d+).*$',text,re.M))
    for cycle,start in enumerate(starts):
        end=re.search(r'^LIFECYCLE_END cycle='+str(cycle)+r' status=0$',text[start.start():],re.M)
        part=text[start.start():start.start()+end.end()]
        frames=[tuple(map(int,m)) for m in re.findall(r'ADAPT_FRAME phase=\d+ request=(\d+) sequence=(\d+) timestamp=(\d+)',part)]
        for _,sequence,timestamp in frames:
            assert timestamp in paired and paired[timestamp][0]['sequence']==sequence
            consumed+=1
        for before,after in zip(frames,frames[1:]):
            if after[1]==before[1]+1:continue
            left,lq=paired[before[2]];right,rq=paired[after[2]];assert lq['owner']==rq['owner']
            owner=lq['owner']
            window=[e for e in events if e.get('owner')==owner and left['ns']<e['ns']<=right['ns']]
            done=[e for e in window if e['kind']=='vb2_buf_done']
            assert len(done)==1 and done[0]['timestamp']==rq['timestamp']
            missing=list(range(before[1]+1,after[1]));epoch=cycle+1
            pd10=all(re.search(r'PD10_READY epoch='+str(epoch)+' sof='+str(sof)+r'\b',part) for sof in missing)
            stats=all(re.search(r'IPE_OBSERVE epoch='+str(epoch)+' sof='+str(sof)+r'\b',part) for sof in missing)
            minimum_owned=min([lq['owned_by_drv']]+[e['owned_by_drv'] for e in window if 'owned_by_drv' in e])
            minimum_queued=min([lq['queued']]+[e['queued'] for e in window if 'queued' in e])
            rows.append(dict(capture=name,cycle=cycle,width=int(start[2]),height=int(start[3]),after=before[1],before=after[1],
                missing=missing,pd10_present=pd10,statistics_present=stats,full_successful_dq_for_missing=False,
                extra_full_vb2_done_between_neighbours=False,neighbour_dq_interval_ms=round((right['ns']-left['ns'])/1e6,3),
                full_queue_event_snapshots=len(window),minimum_owned_snapshot=minimum_owned,minimum_queued_snapshot=minimum_queued,
                physical_dma_fifo_or_root_cause_proven=False))
assert consumed==285 and len(rows)==2
report=dict(stage=461,passed=True,full_v4l2_dq=286,all_dq_uniquely_paired_to_vb2_dq=True,
    all_consumed_images_matched_actual_full_dq=consumed,full_minor=selection['full_minor'],
    bounded_trace_overrun=0,rows=rows,source_completed_not_consumed=286-consumed,
    camera_drop_root_cause_proven=False,phone_accessed=False)
(root.parent/'new-gaps-audit-private.json').write_text(json.dumps(report,indent=2)+'\n')
public=Path(__file__).resolve().parent/'full-gap-validation.json'
public.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
