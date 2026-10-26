from pathlib import Path
import hashlib,json,sys,tarfile,urllib.request
import host
root=host.PRIVATE/'mm-sdk-apks';packages={}
for repo in ['main','community']:
 with tarfile.open(root/(repo+'-APKINDEX.tar.gz')) as tar:text=tar.extractfile('APKINDEX').read().decode()
 for paragraph in text.split('\n\n'):
  d=dict(line.split(':',1) for line in paragraph.splitlines() if ':' in line)
  if 'P' in d:packages[d['P']]=(repo,d)
report=[]
for name in sys.argv[1:]:
 repo,p=packages[name];filename=name+'-'+p['V']+'.apk';url='https://dl-cdn.alpinelinux.org/alpine/edge/'+repo+'/aarch64/'+filename
 path=root/filename
 if not path.exists():path.write_bytes(urllib.request.urlopen(url,timeout=40).read())
 host.upload(path,'/var/lib/samurai/k190-mm-sdk-host-apks/'+filename)
 report.append(dict(package=name,version=p['V'],url=url,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),depends=p.get('D','')))
(root/('extra-'+sys.argv[1]+'-manifest.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
