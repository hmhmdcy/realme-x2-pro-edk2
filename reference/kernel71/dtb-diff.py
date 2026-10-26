from pathlib import Path
import runpy, json, struct
root=Path('/mnt/e/edk2-samurai-out/kernel71')
s=Path('/mnt/e/edk2-samurai-out/kernel68/verify-firmware.py').read_text()
ns={}
exec(s[:s.index('before_dt=')],ns)
parse=ns['fdt_nodes']
a=parse((root/'samurai-before.dtb').read_bytes())
b=parse((root/'samurai-after.dtb').read_bytes())
am={struct.unpack('>I',v['phandle'])[0]:p for p,v in a.items() if 'phandle' in v}
bm={struct.unpack('>I',v['phandle'])[0]:p for p,v in b.items() if 'phandle' in v}
added={p:{k:v.hex() for k,v in b[p].items()} for p in b.keys()-a.keys()}
changes=[]
for p in a.keys()&b.keys():
 for k in a[p].keys()|b[p].keys():
  x,y=a[p].get(k),b[p].get(k)
  if x!=y:
   changes.append(dict(path=p,property=k,before=None if x is None else x.hex(),after=None if y is None else y.hex()))
result=dict(added=added,removed=sorted(a.keys()-b.keys()),changes=changes,
            phandle_before=am,phandle_after=bm)
(root/'dtb-diff.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(added=list(added),removed=result['removed'],changes=changes),indent=2))
