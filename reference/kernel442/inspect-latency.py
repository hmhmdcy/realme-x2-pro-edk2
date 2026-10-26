"""Locate worker-loop stalls in retained 441 logs without exposing IQ values."""
from pathlib import Path
import json,re
import host
P=host.PRIVATE;rows=[]
for attempt in ['r3','r5','r6','r7']:
 root=P.parent/'kernel441'/('runtime-collected-'+attempt)
 for folder in sorted(root.glob('*-isolated')):
  lines=(folder/'client.log').read_text().splitlines()
  parsed=[]
  for index,line in enumerate(lines):
   m=re.match(r'\[(\d+):(\d+):(\d+\.\d+)\]\s+\[(\d+)\].*?\b(CamssVfe|IPACamss)\s+\S+:\d+\s+(.*)',line)
   if not m:continue
   stamp=3600*int(m[1])+60*int(m[2])+float(m[3]);tag=m[6].split()[0];sof=re.search(r'(?:\bsof|statistics-sof)=(\d+)',m[6])
   parsed.append(dict(index=index,time=stamp,pid=int(m[4]),module=m[5],tag=tag,sof=int(sof[1]) if sof else None))
  worker={x['pid'] for x in parsed if x['tag']=='IPE_PAIR'};assert len(worker)==1
  selected=[x for x in parsed if x['pid'] in worker];gaps=[]
  for a,b in zip(selected,selected[1:]):
   gap=b['time']-a['time']
   if gap<.025:continue
   middle=lines[a['index']+1:b['index']]
   gaps.append(dict(ms=round(gap*1000,3),before=a['tag'],after=b['tag'],before_sof=a['sof'],after_sof=b['sof'],app_samples=sum(l.startswith('SAMPLE ') for l in middle),app_frames=sum(l.startswith('ADAPT_FRAME ') for l in middle),nested_ipa_lines=sum('IPACamss ' in l for l in middle)))
  rows.append(dict(attempt=attempt,capture=folder.name,worker_gaps_over25ms=len(gaps),largest=sorted(gaps,key=lambda x:x['ms'],reverse=True)[:8]))
(P/'cached-latency-private.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps(rows,indent=2))
