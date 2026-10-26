"""Read one primary OEM source-directory listing, no Git operation."""
from pathlib import Path
import hashlib,json,urllib.request
HERE=Path(__file__).resolve().parent
url='https://api.github.com/repos/realme-kernel-opensource/realmeX2Pro-kernel-source/contents/drivers/usb/pd?ref=9668fcdc6ec15be7a10d66f7b93c347829e0fdb6'
try:
 with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'source-review','Accept':'application/vnd.github+json'}),timeout=25) as response:raw=response.read(500000)
 entries=json.loads(raw)
 result=dict(url=url,sha256=hashlib.sha256(raw).hexdigest(),entries=[{k:x.get(k) for k in ['name','path','download_url']} for x in entries])
except Exception as e:result=dict(url=url,error=type(e).__name__,message=str(e))
(HERE/'primary-directory-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
