"""Fetch only the missing fixed-revision Gamma schema and setting references."""
from pathlib import Path
import hashlib,json,urllib.request
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
commit='9f17f1b568626b393e785b369c5dc94543774d7a'
paths=['chi-cdk/api/chromatix/XSD/isp/gamma_1_6_0.xsd',
 'camx/src/hwl/iqinterpolation/gamma16interpolation.cpp',
 'camx/src/hwl/iqsetting/gamma16setting.cpp','camx/src/hwl/iqsetting/gamma16setting.h',
 'camx/src/hwl/isphwsetting/titan17x/camxifegamma16titan17x.cpp']
dest=P/'sources';dest.mkdir(exist_ok=True);records=[]
for path in paths:
 target=dest/Path(path).name;url='https://raw.githubusercontent.com/bjzhou/CamxChi/'+commit+'/'+path
 if not target.exists():
  data=urllib.request.urlopen(url,timeout=40).read();assert data and b'404: Not Found' not in data
  target.write_bytes(data)
 data=target.read_bytes();records.append(dict(path=path,url=url,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
 print(path,len(data),flush=True)
(HERE/'primary-sources.json').write_text(json.dumps(dict(commit=commit,files=records),indent=2)+'\n')
