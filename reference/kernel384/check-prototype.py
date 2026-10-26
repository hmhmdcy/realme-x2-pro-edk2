from pathlib import Path
import importlib.util,json,sys
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent/'kernel383'))
from engine_model import prepare
spec=importlib.util.spec_from_file_location('bp',HERE/'bypass-prototype.py');bp=importlib.util.module_from_spec(spec);spec.loader.exec_module(bp)
P=Path('/mnt/e/edk2-samurai-out/kernel383');OUT=P.parent/'kernel384';rows=[]
for w,h in [(640,480),(1920,1080),(4608,3456)]:
 for p in [8,9]:
  for c in [1,2]:
   slug=f'{w}x{h}-p{p}-c{c}';gold=(P/(slug+'-canonical-stripe-private.bin')).read_bytes();candidate=bp.encode(w,h,p,c)
   reads=json.loads((P/(slug+'-reads-private.json')).read_text())
   diffs=[dict(offset=int(k),candidate=candidate[int(k)],original=gold[int(k)]) for k in reads if candidate[int(k)]!=gold[int(k)]]
   _,gj,gc,_=prepare(gold,w,h,p,c)
   try:
    _,cj,cc,_=prepare(candidate,w,h,p,c)
    row=dict(width=w,height=h,port=p,cores=c,different_cdm_bytes=sum(x!=y for x,y in zip(cc,gc)),job_equal=cj==gj,read_field_difference_bytes=len(diffs))
   except Exception as error:row=dict(width=w,height=h,port=p,cores=c,error=str(error),read_field_difference_bytes=len(diffs))
   rows.append(row);(OUT/(slug+'-prototype-private.bin')).write_bytes(candidate);(OUT/(slug+'-prototype-diffs-private.json')).write_text(json.dumps(diffs,indent=2)+'\n');print(json.dumps(row),flush=True)
(OUT/'prototype-result-private.json').write_text(json.dumps(rows,indent=2)+'\n')
