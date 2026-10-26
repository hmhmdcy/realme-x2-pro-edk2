"""Narrow exact downstream build/PHY sources after directory API rate limit."""
from pathlib import Path
import hashlib,json,urllib.request
HERE=Path(__file__).resolve().parent
OUT=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/pd5v-oem-private')
commit='9668fcdc6ec15be7a10d66f7b93c347829e0fdb6'
base='https://raw.githubusercontent.com/realme-kernel-opensource/realmeX2Pro-kernel-source/'+commit+'/'
rows=[]
for name in ['drivers/usb/pd/Makefile','drivers/usb/pd/phy-msm-usbpd.c','drivers/usb/pd/policy_engine.c','drivers/usb/pd/usbpd.h']:
 path=OUT/name.replace('/','--');row=dict(path=name,url=base+name,private_path=str(path))
 try:
  if path.exists():raw=path.read_bytes();row['cached']=True
  else:
   with urllib.request.urlopen(urllib.request.Request(base+name,headers={'User-Agent':'source-review'}),timeout=18) as response:raw=response.read(1200001)
   assert len(raw)<=1200000;path.write_bytes(raw);row['cached']=False
  row.update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
 except Exception as e:row.update(error=type(e).__name__,message=str(e))
 rows.append(row)
(HERE/'primary-exact-manifest.json').write_text(json.dumps(dict(commit=commit,records=rows),indent=2)+'\n')
print(json.dumps(rows,indent=2))
