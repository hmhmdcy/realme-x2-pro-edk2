"""One exact same-board official Android-R PHY source, private raw only."""
from pathlib import Path
import hashlib,json,urllib.request
HERE=Path(__file__).resolve().parent
commit='23172a1571bd91156032cc9fef16284a82b63d2c'
relative='drivers/usb/pd/qpnp-pdphy.c'
url='https://raw.githubusercontent.com/realme-kernel-opensource/realmeX2pro-X3-AndroidR-kernel-source/'+commit+'/'+relative
out=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/pd5v-oem-private/androidr--qpnp-pdphy.c')
r=dict(url=url,commit=commit,path=relative,private_path=str(out))
try:
 if out.exists():raw=out.read_bytes();r['cached']=True
 else:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'source-review'}),timeout=25) as response:raw=response.read(500000)
  assert len(raw)<500000;out.write_bytes(raw);r['cached']=False
 r.update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
except Exception as e:r.update(error=type(e).__name__,message=str(e))
(HERE/'androidr-source-result.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(r,indent=2))
