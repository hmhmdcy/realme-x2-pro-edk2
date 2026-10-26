"""Fetch pinned public diagnostic source, without executing remote code."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from urllib.request import Request,urlopen
import base64,hashlib,json,os

os.umask(0o077)
here=Path(__file__).resolve().parent
out=Path('/mnt/e/edk2-samurai-out/kernel208/receiver-sources')
out.mkdir(mode=0o700)
commit='57ced1dc07cd15aaedbee0f98a3384ac837c4ce5'
base='https://android.googlesource.com/platform/hardware/qcom/sm8150/gps/+/'+commit+'/'
paths=['core/SystemStatus.cpp','core/SystemStatus.h','core/LocAdapterBase.h']
def fetch(path):
    url=base+path+'?format=TEXT'
    try:
        with urlopen(Request(url,headers={'User-Agent':'samurai-receiver-source-review'}),timeout=35) as response:
            data=base64.b64decode(response.read(3_000_000),validate=True)
        (out/path.replace('/','__')).write_bytes(data)
        return path,dict(url=url,bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
    except Exception as error:
        (out/(path.replace('/','__')+'.failure.txt')).write_text(type(error).__name__+': '+str(error))
        return path,dict(failed=True,error_type=type(error).__name__)
with ThreadPoolExecutor(max_workers=3) as pool:
    files=dict(pool.map(fetch,paths))
report=dict(stage=208,official_pinned_commit=commit,files=files,remote_code_executed=False)
(here/'receiver-source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
