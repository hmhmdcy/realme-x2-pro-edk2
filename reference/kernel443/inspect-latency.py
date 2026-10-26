"""Locate retained normal-consumer latency intervals without another capture."""
from pathlib import Path
import collections,json,re,statistics,sys
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
attempt=sys.argv[1] if len(sys.argv)>1 else 'r1';root=P/('runtime-collected-'+attempt)
labels={
 'pd10':r'PD10_READY epoch=1 sof=(\d+)',
 'observe':r'IPE_OBSERVE epoch=1 sof=(\d+)',
 'wb':r'WB context epoch=1 sof=(\d+)',
 'pair':r'IPE_PAIR epoch=1 sof=(\d+)',
 'prepare':r'IPE_TONE_PREPARE epoch=1 sof=(\d+)',
 'queue':r'IPE_TONE_QUEUE epoch=1 sof=(\d+)',
 'receipt':r'IPE_RECEIPT epoch=1 sof=(\d+)',
}
private=[];rows=[]
for folder in sorted(root.glob('*-native'))+sorted(root.glob('*-isolated')):
 text=(folder/'client.log').read_text();events=collections.defaultdict(dict)
 for line in text.splitlines():
  stamp=re.match(r'\[(\d+):(\d+):(\d+)\.(\d{9})\]',line)
  if not stamp:continue
  h,m,s,ns=map(int,stamp.groups());t=((h*60+m)*60+s)*1000000000+ns
  for label,pattern in labels.items():
   match=re.search(pattern,line)
   if match:
    sof=int(match[1]);assert label not in events[sof];events[sof][label]=t
 samples=[tuple(map(int,m)) for m in re.findall(r'GST_IMAGE .* sequence=(\d+) wall-ns=(\d+)',text)]
 consumed={s for s,t in samples};metrics={}
 for left,right in [('pd10','queue'),('observe','queue'),('pair','queue'),('queue','receipt')]:
  values=[(sof,(e[right]-e[left])/1e6) for sof,e in events.items() if sof in consumed and left in e and right in e]
  assert values and all(ms>=0 for sof,ms in values)
  xs=sorted(ms for sof,ms in values);key=left+'_to_'+right
  metrics[key]=dict(frames=len(xs),median_ms=round(statistics.median(xs),3),p95_ms=round(xs[min(len(xs)-1,len(xs)*95//100)],3),maximum_ms=round(xs[-1],3),maximum_sof=max(values,key=lambda x:x[1])[0])
  private.append(dict(capture=folder.name,interval=key,values=values))
 gaps=[dict(after_sof=a[0],before_sof=b[0],missing=b[0]-a[0]-1,steady=i>=8) for i,(a,b) in enumerate(zip(samples,samples[1:])) if b[0]>a[0]+1]
 rows.append(dict(capture=folder.name,intervals=metrics,kernel_sequence_gaps=gaps,steady_missing_sofs=sum(g['missing'] for g in gaps if g['steady'])))
(P/'normal-consumer-latencies-private.json').write_text(json.dumps(private,indent=2)+'\n')
r=dict(stage=443,attempt=attempt,rows=rows,cached_logs_only=True,intervals_do_not_isolate_individual_synchronous_call_cost=True,root_cause_claimed=False,passed=True)
(HERE/'latency-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
