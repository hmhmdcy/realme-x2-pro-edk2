"""Fetch the exact posted series; never treat a similarly named WIP branch as that series."""
from pathlib import Path
import gzip,hashlib,json,subprocess,urllib.request
import host
R=Path(__file__).resolve().parent;P=host.PRIVATE;records=[]
urls=[('tests-readme','https://raw.githubusercontent.com/0xB0D/ife-tests/master/README.md'),
 ('series-mbox','https://lore.kernel.org/all/20261005-linux-mainline-7-2-sm8650-hdk-rfc-0-v1-0-ed985aefd611@kernel.org/t.mbox.gz')]
for name,url in urls:
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'b4/0.14 Samurai-camera-audit'}),timeout=35) as r:data=r.read(20*1024*1024);kind=r.headers.get('Content-Type')
  (P/(name+'-download-private')).write_bytes(data);records.append(dict(url=url,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),content_type=kind))
  if name=='tests-readme':print(data.decode()[:6500])
  elif data.startswith(b'\x1f\x8b'):
   raw=gzip.decompress(data);(P/'inline-proposal.mbox').write_bytes(raw);print('Exact series gzip:',len(raw),'bytes')
  else:print('Series endpoint did not return gzip:',data[:140].decode(errors='replace'))
 except Exception as e:records.append(dict(url=url,error=str(e)));print(name,'unavailable:',str(e))
repo='/home/cy122/x2pro-linux/camss-isp279-upstream.git'
print('WIP branch:',subprocess.check_output(['git','-C',repo,'show','-s','--format=%H %aI %s','HEAD'],text=True).strip())
q=subprocess.run(['git','ls-remote','https://github.com/0xB0D/linux.git','HEAD'],capture_output=True,text=True,timeout=35);print('Maintainer default:',q.stdout.strip())
(R/'inline-source-fetch-validation.json').write_text(json.dumps(dict(stage=279,sources=records,phone_unchanged=True),indent=2)+'\n')
