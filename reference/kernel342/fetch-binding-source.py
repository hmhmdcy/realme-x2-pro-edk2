from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,urllib.request
import host
P=host.PRIVATE;commit='36fc163a534963a5b3af52186af5efcc63401ad2';directory=P/'sources';directory.mkdir(exist_ok=True)
paths=['camx/src/core/camximagesensormoduledata.cpp','camx/src/core/sensor/camximagesensormoduledata.cpp','camx/src/core/chi/camximagesensormoduledata.cpp']
def fetch(path):
 url='https://raw.githubusercontent.com/comprehensive9/vendor_qcom_proprietary/'+commit+'/'+path
 try:
  raw=urllib.request.urlopen(url,timeout=18).read();assert len(raw)<2*1024*1024
  (directory/Path(path).name).write_bytes(raw);return dict(path=path,url=url,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
 except Exception as e:return dict(path=path,error=str(e))
with ThreadPoolExecutor(max_workers=3) as pool:rows=list(pool.map(fetch,paths))
(P/'binding-source-fetch-private.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows))
