from pathlib import Path
import hashlib,json,urllib.request
P=Path('/mnt/e/edk2-samurai-out/kernel245/memshare-source');assert not P.exists();P.mkdir(mode=0o700)
commit='23172a1571bd91156032cc9fef16284a82b63d2c';root='https://raw.githubusercontent.com/realme-kernel-opensource/realmeX2pro-X3-AndroidR-kernel-source/'+commit+'/drivers/soc/qcom/memshare/'
manifest={}
for name in ['msm_memshare.h','msm_memshare.c','heap_mem_ext_v01.h','heap_mem_ext_v01.c']:
 url=root+name;b=urllib.request.urlopen(url,timeout=30).read();assert 100<len(b)<150000;(P/name).write_bytes(b);manifest[name]=dict(url=url,bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
(P/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(dict(stage=245,source_commit=commit,files={k:dict(bytes=v['bytes'],sha256=v['sha256']) for k,v in manifest.items()})))
