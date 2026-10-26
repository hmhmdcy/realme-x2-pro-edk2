"""Join independently completed image/PD10/statistics by kernel SOF, privately."""
from pathlib import Path
import collections,hashlib,json,re,struct,sys
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;attempt=sys.argv[1] if len(sys.argv)>1 else 'r1'
root=P/('runtime-collected-'+attempt);out={}
for label in ['pattern','scene']:
 path=root/label/'capture.log'
 if not path.exists():continue
 rows={};stats={};params=[]
 for line in path.read_text().splitlines():
  fields=dict(re.findall(r'(\w+)=([^ ]+)',line))
  if line.startswith('GTM_FRAME '):rows.setdefault(int(fields['sequence']),{})[fields['kind']]=fields
  if line.startswith('GTM_STATS '):stats[int(fields['sequence'])]={k:int(v) for k,v in fields.items()}
  if line.startswith('GTM_PARAM_Q '):params.append(fields)
 groups=collections.defaultdict(list)
 for sof,s in stats.items():
  f=rows.get(sof,{});assert set(f)=={'full','ds4'}
  raw=(root/label/('stats-'+str(sof)+'.bin')).read_bytes();version,size=struct.unpack_from('<II',raw);assert version==1 and len(raw)==size+8
  at=8;receipt=None
  while at<len(raw):
   typ,flags,n=struct.unpack_from('<HHI',raw,at);assert n>=8 and n%8==0 and at+n<=len(raw)
   if typ==3:receipt=struct.unpack_from('<QQII',raw,at+8)
   at+=n
  assert receipt==(s['cookie'],s['generation'],s['status'],s['bank'])
  for kind in ['full','ds4']:assert (root/label/(kind+'-'+str(sof)+'.bin')).exists()
  groups[s['cookie']&0xff].append(dict(sof=sof,**{k:s[k] for k in ['generation','status','bank']},full=f['full']['active_hash'],pd10=f['ds4']['active_hash']))
 public=[]
 for phase,frames in sorted(groups.items()):
  public.append(dict(packet_index=phase-1,frames=len(frames),sof=[x['sof'] for x in frames],banks=sorted({x['bank'] for x in frames}),generations=sorted({x['generation'] for x in frames}),full_active_hash_counts=dict(collections.Counter(x['full'] for x in frames)),pd10_active_hash_counts=dict(collections.Counter(x['pd10'] for x in frames))))
 out[label]=dict(joined_same_sof=len(stats),packet_groups=public)
 (P/(label+'-'+attempt+'-sof-join-private.json')).write_text(json.dumps(dict(groups=groups,params=params),indent=2)+'\n')
r=dict(stage=434,attempt=attempt,captures=out,grouping_by_actual_stats_receipt_not_proposed_phase=True,private_receipts_validated=True)
(HERE/('capture-analysis-'+attempt+'.json')).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
