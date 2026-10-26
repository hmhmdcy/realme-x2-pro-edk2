"""Read pinned CamX rolloff math and Titan17x packing sources, without executing them."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,urllib.request
import host
HERE=Path(__file__).resolve().parent;cache=host.PRIVATE/'sources';cache.mkdir(exist_ok=True)
commit='36fc163a534963a5b3af52186af5efcc63401ad2'
paths=['camx/src/hwl/ispiqmodule/camxifelsc34.cpp',
 'camx/src/hwl/isphwsetting/titan17x/camxifelsc34titan17x.cpp',
 'camx/src/hwl/iqsetting/lsc34setting.cpp',
 'camx/src/hwl/iqinterpolation/lsc34interpolation.cpp',
 'camx/src/hwl/iqsetting/lsc34setting.h',
 'camx/src/hwl/isphwsetting/titan17x/camxifelsc34titan17x.h',
 'chi-cdk/api/chromatix/XSD/isp/lsc_3_4_0.xsd']
def fetch(relative):
 target=cache/Path(relative).name
 url='https://raw.githubusercontent.com/comprehensive9/vendor_qcom_proprietary/'+commit+'/'+relative
 try:
  if not target.exists():target.write_bytes(urllib.request.urlopen(url,timeout=25).read())
  raw=target.read_bytes()
  return dict(path=relative,url=url,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
 except Exception as exc:return dict(path=relative,url=url,error=str(exc))
with ThreadPoolExecutor(max_workers=4) as pool:records=list(pool.map(fetch,paths))
(HERE/'lsc-primary-sources.json').write_text(json.dumps(dict(stage=317,commit=commit,files=records),indent=2)+'\n')
print(json.dumps(records,indent=2))
