"""Record original full-frame NV12 partition boundaries for native implementation."""
from pathlib import Path
import importlib.util,json,struct
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('sl383',HERE/'trace-striping.py');sl=importlib.util.module_from_spec(spec);spec.loader.exec_module(sl)
rows=[]
for width in [128,160,256,318,320,322,326,328,330,334,336,338,638,640,642,650,656,658,660,662,664,666,670,672,674,960,1280,1312,1920,3840,4608]:
 for cores in [1,2]:
  try:
   blob,mask,writes,info=sl.execute(width,480,8,cores)
   assert info['passes']==1
   parts=[]
   for i in range(info['stripes'][0]):
    off=2268+i*624;parts.append(dict(fetch=list(struct.unpack_from('<HH',blob,off+4)),output=list(struct.unpack_from('<HH',blob,off+20))))
   row=dict(width=width,cores=cores,parts=parts,success=True)
  except Exception as error:row=dict(width=width,cores=cores,success=False,error=str(error))
  rows.append(row)
(P/'partition-probe-private.json').write_text(json.dumps(rows,indent=2)+'\n')
for row in rows:
 print(json.dumps(dict(width=row['width'],cores=row['cores'],success=row['success'],stripes=len(row.get('parts',[])),parts=row.get('parts',[])[:4])))
