from pathlib import Path
import importlib.util,json,struct
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
module('storage284',HERE.parent/'kernel284/storage.py').mounted_build();n=module('native425',HERE/'native-model.py');m=n.Native();rows=[]
for w,h in [(2,2),(4,4),(48,54),(72,54),(74,56),(96,58),(98,60),(144,106),(146,108),(160,120),(162,122),(190,214),(192,216),(194,218),(200,240),(288,216),(290,218),(480,270),(1152,864),(2048,2048)]:
 image,descriptor=m.pd10(w,h);values=struct.unpack_from('<4I',image,24);size=struct.unpack_from('<Q',image,56)[0]
 row=dict(width=w,height=h,plane_width=values[0],plane_height=values[1],stride=values[2],slice_height=values[3],bytes=size)
 rows.append(row)
(P/'pd10-layout-probe-private.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows,indent=2))
