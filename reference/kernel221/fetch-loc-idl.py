from pathlib import Path
from urllib.request import Request,urlopen
import hashlib,json,os,subprocess,re
out=Path('/mnt/e/edk2-samurai-out/kernel221/loc-upstream');out.mkdir(mode=0o700)
url='https://github.com/qualcomm-linux/location-apis-qcom.git'
p=subprocess.run(['git','ls-remote',url,'refs/heads/location.lnx.0.0'],capture_output=True,timeout=60,check=True)
commit=p.stdout.split()[0].decode();assert re.fullmatch('[0-9a-f]{40}',commit)
files={}
for relative in ['loc_api/loc_api_v02/location_service_v02.h','loc_api/loc_api_v02/location_service_v02.c','loc_api/loc_api_v02/LocApiV02.cpp']:
 public='https://raw.githubusercontent.com/qualcomm-linux/location-apis-qcom/'+commit+'/'+relative
 data=urlopen(Request(public,headers={'User-Agent':'samurai-linux-source-review'}),timeout=40).read(3_000_001);assert len(data)<3_000_001
 name=relative.rsplit('/',1)[1];(out/name).write_bytes(data)
 files[name]=dict(url=public,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))
 report=[]
 terms=['GetGnss','GET_GNSS','gnssConstellation','getGpsLock','setGpsLock','setGnssSvTypeConfig','getGnssSvTypeConfig','LOC_SET_BLACKLIST','getSvBlacklist']
 lines=data.decode().splitlines();indices=[i for i,l in enumerate(lines) if any(s in l for s in terms)]
 for i,l in enumerate(lines):
  if any(abs(i-j)<7 for j in indices):report.append(str(i+1)+': '+l)
 (out/(name+'.selected.txt')).write_text('\n'.join(report)+'\n')
r=dict(stage=221,repository=url,commit=commit,files=files,source_review_only=True)
here=Path(__file__).resolve().parent;(here/'qualcomm-loc-source-validation.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(r))
