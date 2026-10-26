from pathlib import Path
import importlib.util,json,sys,struct
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent/'kernel383'))
from engine_model import prepare
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
bp=load('bp',HERE/'bypass-prototype.py');sl=load('sl',HERE.parent/'kernel383/trace-striping.py')
OUT=Path('/mnt/e/edk2-samurai-out/kernel384');rows=[]
cases=[(128,128),(160,130),(256,256),(318,478),(328,482),(330,128),(638,416),(642,722),(656,480),(658,1082),(728,416),(2048,1536),(4096,3072),(8192,480)]
for w,h in cases:
 for c in [1,2]:
  p=8 if c==1 else 9;slug=f'{w}x{h}-p{p}-c{c}'
  a,_,_,info=sl.execute(w,h,p,c,dirty=0xa5);b,_,_,_=sl.execute(w,h,p,c,dirty=0x5a)
  canonical=bytes(x&~(x^y)&255 for x,y in zip(a,b));candidate=bp.encode(w,h,p,c)
  _,gj,gc,reads=prepare(canonical,w,h,p,c,observe=True)
  _,uj,uc,_=prepare(a,w,h,p,c);assert uj==gj and uc==gc
  diffs=[dict(offset=k,candidate=candidate[k],original=canonical[k]) for k in reads if candidate[k]!=canonical[k]]
  try:
   _,cj,cc,_=prepare(candidate,w,h,p,c)
   row=dict(width=w,height=h,port=p,cores=c,different_cdm_bytes=sum(x!=y for x,y in zip(cc,gc)),job_equal=cj==gj,read_field_difference_bytes=len(diffs),grid_y=struct.unpack_from('<H',canonical,108)[0],grid_x=struct.unpack_from('<H',canonical,2400)[0])
  except Exception as error:row=dict(width=w,height=h,port=p,cores=c,error=str(error),read_field_difference_bytes=len(diffs))
  rows.append(row)
  for name,data in [('canonical-stripe',canonical),('original-cdm',gc),('prototype',candidate)]: (OUT/(slug+'-'+name+'-private.bin')).write_bytes(data)
  (OUT/(slug+'-prototype-diffs-private.json')).write_text(json.dumps(diffs,indent=2)+'\n');print(json.dumps(row),flush=True)
(OUT/'extra-prototype-result-private.json').write_text(json.dumps(rows,indent=2)+'\n')
