"""Cache only the pinned CAMSS ICP/BPS/IPE prototype files required here."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import base64,hashlib,json,urllib.request
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;directory=P/'upstream';directory.mkdir(exist_ok=True)
commit='ebd1e440443121d18f730ab2aeea5586a754f36f';base='https://kernel.googlesource.com/pub/scm/linux/kernel/git/bod/linux/+/'
paths=['drivers/media/platform/qcom/camss/'+f for f in ['camss-icp.c','camss-icp.h','camss-icp-hfi.h','camss-ipe.c','camss-ipe.h','camss-bps.c','camss-bps.h','Makefile','Kconfig']]
def fetch(path):
 target=directory/Path(path).name
 if not target.exists():
  raw=urllib.request.urlopen(base+commit+'/'+path+'?format=TEXT',timeout=35).read();target.write_bytes(base64.b64decode(raw))
 data=target.read_bytes();return dict(path=path,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),url=base+commit+'/'+path)
with ThreadPoolExecutor(max_workers=4) as pool:records=list(pool.map(fetch,paths))
(HERE/'upstream-sources.json').write_text(json.dumps(dict(stage=352,commit=commit,files=records),indent=2)+'\n')
print(json.dumps(dict(files=len(records),bytes=sum(r['bytes'] for r in records),commit=commit),indent=2))
