"""Reuse the FULL event parser on the cached tele window; no device access."""
from pathlib import Path
import hashlib,json,re
HERE=Path(__file__).resolve().parent;root=Path('/mnt/e/edk2-samurai-out/kernel467/runtime-collected-r1')
original=(HERE.parent/'kernel461/inspect-full-gaps.py').read_text()
prefix=original[:original.index("dq=[e for e in events")]
prefix=prefix.replace('kernel461/runtime-collected-r2','kernel467/runtime-collected-r1')
namespace={};exec(compile(prefix,'retained461-full-event-parser','exec'),namespace)
events=namespace['events'];selection=namespace['selection']
dq=[e for e in events if e['kind']=='v4l2_dqbuf' and e['minor']==selection['full_minor']]
assert len(dq)==65
paired={}
for event in dq:
    matches=[v for v in events if v['kind']=='vb2_dqbuf' and v['pid']==event['pid'] and v['index']==event['index']
        and v['timestamp']//1000*1000==event['timestamp'] and 0<=event['ns']-v['ns']<2_000_000]
    assert len(matches)==1;paired[event['timestamp']]=(event,matches[0])
rows=[]
for case in ['1280x720-isolated','1920x1080-isolated']:
    text=(root/case/'client.log').read_text()
    times=[((int(h)*60+int(m))*60+int(s))*10**9+int(ns) for h,m,s,ns in re.findall(r'\[(\d+):(\d+):(\d+)\.(\d{9})\]',text)]
    case_dq=[e for e in dq if min(times)<=e['ns']<=max(times)]
    sequences=[int(v) for v in re.findall(r'GST_IMAGE frame=\d+ .*? sequence=(\d+) ',text)]
    assert len(sequences)==32
    for before,after in zip(sequences,sequences[1:]):
        if after==before+1:continue
        l=[e for e in case_dq if e['sequence']==before];r=[e for e in case_dq if e['sequence']==after]
        assert len(l)==len(r)==1;left,lq=paired[l[0]['timestamp']];right,rq=paired[r[0]['timestamp']]
        assert lq['owner']==rq['owner'];owner=lq['owner']
        window=[e for e in events if e.get('owner')==owner and left['ns']<e['ns']<=right['ns']]
        done=[e for e in window if e['kind']=='vb2_buf_done'];missing=list(range(before+1,after))
        rows.append(dict(capture=case,after_sof=before,before_sof=after,missing_sofs=missing,
            pd10_present=all(re.search(r'PD10_READY epoch=1 sof='+str(sof)+r'\b',text) for sof in missing),
            statistics_present=all(re.search(r'IPE_OBSERVE epoch=1 sof='+str(sof)+r'\b',text) for sof in missing),
            successful_full_dq_for_missing=any(e['sequence'] in missing for e in case_dq),
            full_vb2_done_between_neighbours=len(done),
            only_following_neighbour_vb2_done=len(done)==1 and done[0]['timestamp']==rq['timestamp'],
            minimum_owned_snapshot=min([lq['owned_by_drv']]+[e['owned_by_drv'] for e in window if 'owned_by_drv' in e]),
            minimum_queued_snapshot=min([lq['queued']]+[e['queued'] for e in window if 'queued' in e]),
            neighbour_dq_interval_ms=round((right['ns']-left['ns'])/1e6,3),physical_root_cause_proven=False))
assert len(rows)==3
report=dict(stage=467,passed=True,cached_only=True,full_dq=65,consumed=64,
    reused_parser_sha256=hashlib.sha256(prefix.encode()).hexdigest(),rows=rows,
    source_completed_full_not_ipe_or_consumed=1,production_tuning_or_capacity_policy_changed=False)
(HERE/'gap-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
