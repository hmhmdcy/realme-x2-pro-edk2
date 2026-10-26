from pathlib import Path
import hashlib,json,tarfile,urllib.request
import host
root=host.PRIVATE/'mm-sdk-apks'
with tarfile.open(root/'main-APKINDEX.tar.gz') as tar:text=tar.extractfile('APKINDEX').read().decode()
packages={}
for paragraph in text.split('\n\n'):
 d=dict(line.split(':',1) for line in paragraph.splitlines() if ':' in line)
 if 'P' in d:packages[d['P']]=d
for name in ['gettext','gettext-envsubst','gettext-libs','libxml2','libunistring']:
 p=packages[name];filename=name+'-'+p['V']+'.apk';url='https://dl-cdn.alpinelinux.org/alpine/edge/main/aarch64/'+filename
 data=urllib.request.urlopen(url,timeout=40).read();path=root/filename;path.write_bytes(data);host.upload(path,'/var/lib/samurai/k190-mm-sdk-host-apks/'+filename)
 print(name,p['V'],p.get('D',''))
