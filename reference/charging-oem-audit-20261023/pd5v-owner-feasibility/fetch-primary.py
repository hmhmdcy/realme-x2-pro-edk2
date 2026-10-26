"""Bounded primary OEM source retrieval only; no Git, SDK or device."""
from pathlib import Path
import hashlib,json,urllib.request
HERE=Path(__file__).resolve().parent
OUT=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/pd5v-oem-private')
OUT.mkdir(parents=True,exist_ok=True)
commit='9668fcdc6ec15be7a10d66f7b93c347829e0fdb6'
base='https://raw.githubusercontent.com/realme-kernel-opensource/realmeX2Pro-kernel-source/'+commit+'/'
records=[]
for name in ['drivers/usb/pd/pd_phy.c','drivers/usb/pd/policy_engine.c','include/linux/usb/usbpd.h','include/linux/usb/pd.h']:
 dest=OUT/name.replace('/','--');record=dict(path=name,url=base+name,private_path=str(dest))
 try:
  if dest.exists():raw=dest.read_bytes();record['cached']=True
  else:
   with urllib.request.urlopen(urllib.request.Request(base+name,headers={'User-Agent':'source-review'}),timeout=25) as response:
    raw=response.read(1200001)
   assert len(raw)<=1200000
   dest.write_bytes(raw);record['cached']=False
  record.update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
 except Exception as e:record.update(error=type(e).__name__,message=str(e))
 records.append(record)
(HERE/'primary-source-manifest.json').write_text(json.dumps(dict(commit=commit,records=records,Git_invoked=False,device_accessed=False),indent=2)+'\n')
print(json.dumps(records,indent=2))
