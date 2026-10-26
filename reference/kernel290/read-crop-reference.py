"""Read fixed public reference files for register facts; never execute or publish vendor implementations."""
from pathlib import Path
import hashlib,json,urllib.request
import host

ROOT=Path(__file__).resolve().parent
base='https://raw.githubusercontent.com/bjzhou/CamxChi/9f17f1b568626b393e785b369c5dc94543774d7a/'
paths=['camx/src/hwl/ispiqmodule/camxifecrop10.cpp','camx/src/hwl/ispiqmodule/camxifecrop10.h',
 'camx/src/hwl/isphwsetting/titan17x/camxifecrop10titan17x.cpp','camx/src/hwl/isphwsetting/titan17x/camxifecrop10titan17x.h']
rows=[]
for path in paths:
 target=host.PRIVATE/('reference-'+Path(path).name+'-private')
 try:
  assert not target.exists()
  with urllib.request.urlopen(urllib.request.Request(base+path,headers={'User-Agent':'samurai-camera-source-audit'}),timeout=25) as response:data=response.read(300000)
  assert len(data)<300000 and b'IFECrop10' in data;target.write_bytes(data)
  rows.append(dict(path=path,url=base+path,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),read=True))
 except Exception as e:rows.append(dict(path=path,url=base+path,read=False,error=str(e)))
(ROOT/'crop-reference-validation.json').write_text(json.dumps(dict(stage=290,reference_commit='9f17f1b568626b393e785b369c5dc94543774d7a',files=rows,no_downloaded_code_execution=True),indent=2)+'\n')
print(json.dumps(rows,indent=2))
