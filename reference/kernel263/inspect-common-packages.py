"""Read package ownership and preserve production common libraries before deployment."""
from pathlib import Path
import hashlib,json,subprocess,urllib.request
import host
R=Path(__file__).parent
code=r'''
from pathlib import Path
import hashlib,json,subprocess
paths=['/usr/lib/libpipewire-0.3.so.0.1609.0','/usr/lib/spa-0.2/libcamera/libspa-libcamera.so']
results=[]
for name in paths:
 p=Path(name);results.append(dict(path=name,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),owner=subprocess.check_output(['apk','info','--who-owns',name]).decode().strip()))
print(json.dumps(results))
'''
r=host.ssh('python3 -',input=code.encode());items=json.loads(r.stdout)
(host.PRIVATE/'production-common-before-private.json').write_bytes(r.stdout)
for item in items:
 owner=item['owner'].split()[-1]
 for mirror in ['https://dl-cdn.alpinelinux.org/alpine','https://mirrors.ustc.edu.cn/alpine','https://dl.alpinelinux.org/alpine']:
  url=mirror+'/edge/community/aarch64/'+owner+'.apk'
  try:data=urllib.request.urlopen(url,timeout=8).read()
  except Exception as e:item.setdefault('download_errors',[]).append(dict(url=url,error=type(e).__name__));continue
  (host.PRIVATE/(owner+'.apk')).write_bytes(data)
  item.update(apk_sha256=hashlib.sha256(data).hexdigest(),url=url);break
(R/'common-package-inputs-validation.json').write_text(json.dumps(items,indent=2)+'\n');print(json.dumps(items,indent=2))
