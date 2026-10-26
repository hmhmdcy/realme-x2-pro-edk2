"""Diagnose the rejected firmware rebuild without weakening deployment checks."""
from pathlib import Path
import ast
import difflib
import hashlib
import json
import lzma
import struct
import uuid
import zlib

R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel267')
namespace={}
exec(compile((R.parent/'kernel104/verify-firmware.py').read_text().split('dt_audit=')[0],'parser','exec'),namespace)
fv,sections,align,fdt_nodes=(namespace[n] for n in ['fv','sections','align','fdt_nodes'])
dt_guid,lz_guid=(namespace[n] for n in ['dt_guid','lz_guid'])
compat=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150/FdtBlob_compat/samurai.dtb').read_bytes()
tree=ast.parse((R.parent/'kernel219/build-package.py').read_text())
node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='unpack')
exec(compile(ast.Module(body=[node],type_ignores=[]),'unpack','exec'))
old=unpack((P.parent/'kernel235/boot-partition-k235-imx319-p-lab.img').read_bytes())
new=unpack((P/'firmware/boot-candidate-private.img').read_bytes())
report=[]
out=P/'firmware-delta-r2';out.mkdir(mode=0o700)
for guid,m in old['modules'].items():
    n=new['modules'][guid]
    if m['body']==n['body']:continue
    (out/(guid+'-old.bin')).write_bytes(m['body']);(out/(guid+'-new.bin')).write_bytes(n['body'])
    spans=[]
    if guid!=dt_guid and len(m['body'])==len(n['body']):
        positions=[i for i,(a,b) in enumerate(zip(m['body'],n['body'])) if a!=b]
        for i in positions:
            if spans and spans[-1]['end']==i:spans[-1]['end']=i+1
            else:spans.append(dict(start=i,end=i+1))
        for row in spans:
            a,b=row['start'],row['end']
            row.update(old_bytes=m['body'][a:b].hex() if b-a<=16 else None,new_bytes=n['body'][a:b].hex() if b-a<=16 else None)
    row=dict(guid=guid,name=n['name'],old_length=len(m['body']),new_length=len(n['body']),difference_spans=spans)
    report.append(row)
(P/'rejected-firmware-delta-private.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps([dict(name=x['name'],old_length=x['old_length'],new_length=x['new_length'],difference_spans=x['difference_spans'][:12]) for x in report]))
