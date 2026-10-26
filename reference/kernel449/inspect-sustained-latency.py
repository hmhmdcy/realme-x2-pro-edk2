"""Correlate retained consumed SOFs and phase times; no device reads."""
from pathlib import Path
import collections,json,re,statistics
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
root=P/'runtime-collected-r2';text=(root/'user-sustained-1080/client.log').read_text()
events=collections.defaultdict(dict);focus={};dispatch={}
labels={'pd10':'PD10_READY','observe':'IPE_OBSERVE','pair':'IPE_PAIR','queue':'IPE_TONE_QUEUE','receipt':'IPE_RECEIPT'}
for line in text.splitlines():
 stamp=re.match(r'\[(\d+):(\d+):(\d+)\.(\d{9})\]',line)
 if not stamp:continue
 h,m,s,ns=map(int,stamp.groups());t=((h*60+m)*60+s)*10**9+ns
 v=dict(re.findall(r'([a-z][a-z0-9-]*)=([^ ]+)',line));sof=int(v['sof']) if 'sof' in v else None
 for label,marker in labels.items():
  if marker+' ' in line and (label!='receipt' or v['success']=='1'):
   assert label not in events[sof];events[sof][label]=t
 if 'FOCUS_EXECUTION ' in line:focus[sof]={key:int(v[key]) for key in ['sample-wall-us','sample-cpu-us','involuntary','voluntary']}
 if 'FRAME_IPA_PREPARE ' in line:dispatch[sof]=int(v['dispatch-us'])
samples=[tuple(map(int,m)) for m in re.findall(r'GST_IMAGE .* sequence=(\d+) wall-ns=(\d+)',text)]
assert len(samples)==9000
consumed={sof for sof,t in samples};metrics={};private=[]
def quantiles(values):
 xs=sorted(values);assert xs
 return dict(n=len(xs),median_ms=round(statistics.median(xs),3),p95_ms=round(xs[min(len(xs)-1,len(xs)*95//100)],3),p99_ms=round(xs[min(len(xs)-1,len(xs)*99//100)],3),maximum_ms=round(xs[-1],3))
for left,right in [('pd10','queue'),('observe','queue'),('pair','queue'),('queue','receipt')]:
 values=[(sof,(e[right]-e[left])/1e6) for sof,e in events.items() if sof in consumed and left in e and right in e];assert len(values)==9000 and all(ms>=0 for sof,ms in values)
 metrics[left+'_to_'+right]=quantiles([ms for sof,ms in values]);private.append(dict(interval=left+'_to_'+right,values=values))
metrics['focus_dispatch']=quantiles([value/1000 for sof,value in dispatch.items() if sof in consumed])
gaps=[]
for a,b in zip(samples,samples[1:]):
 if b[0]<=a[0]+1:continue
 nearby=[]
 for sof in range(a[0]-3,b[0]+1):
  e=events.get(sof,{})
  nearby.append(dict(sof=sof,consumed=sof in consumed,events=sorted(e),focus_dispatch_ms=round(dispatch[sof]/1000,3) if sof in dispatch else None,focus=focus.get(sof),pair_to_queue_ms=round((e['queue']-e['pair'])/1e6,3) if 'pair' in e and 'queue' in e else None))
 gaps.append(dict(after_sof=a[0],before_sof=b[0],missing=b[0]-a[0]-1,nearby=nearby))
(P/'sustained-latencies-private.json').write_text(json.dumps(dict(intervals=private,gaps=gaps),indent=2)+'\n')
missing={sof for a,b in zip(samples,samples[1:]) for sof in range(a[0]+1,b[0])}
r=dict(stage=449,frames=9000,missing_sofs=len(missing),missing_sofs_with_pd10=sum('pd10' in events.get(s,{}) for s in missing),missing_sofs_with_observation=sum('observe' in events.get(s,{}) for s in missing),missing_sofs_paired=sum('pair' in events.get(s,{}) for s in missing),intervals=metrics,cached_logs_only=True,missing_full_frame_buffer_ownership_not_instrumented=True,drop_root_cause_proven=False,statistics_retirement_fix_does_not_claim_to_fix_gaps=True,passed=True)
(HERE/'latency-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
