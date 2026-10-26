"""Exact PHY source named by the retrieved same-commit OEM Makefile."""
from pathlib import Path
import hashlib,json,urllib.request
HERE=Path(__file__).resolve().parent
name='drivers/usb/pd/qpnp-pdphy.c';commit='9668fcdc6ec15be7a10d66f7b93c347829e0fdb6'
path=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/pd5v-oem-private')/name.replace('/','--')
url='https://raw.githubusercontent.com/realme-kernel-opensource/realmeX2Pro-kernel-source/'+commit+'/'+name
result=dict(path=name,url=url,private_path=str(path))
try:
 if path.exists():raw=path.read_bytes();result['cached']=True
 else:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'source-review'}),timeout=25) as response:raw=response.read(700000)
  assert len(raw)<700000;path.write_bytes(raw);result['cached']=False
 result.update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
except Exception as e:result.update(error=type(e).__name__,message=str(e))
(HERE/'qpnp-source-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
