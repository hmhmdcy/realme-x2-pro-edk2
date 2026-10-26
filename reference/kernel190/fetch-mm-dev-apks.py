from pathlib import Path
import io,tarfile,urllib.request,hashlib,json
root=Path('/mnt/e/edk2-samurai-out/kernel190/mm-sdk-apks');root.mkdir(exist_ok=True)
base='https://dl-cdn.alpinelinux.org/alpine/edge/'
packages={}
for repo in ['main','community']:
    raw=urllib.request.urlopen(base+repo+'/aarch64/APKINDEX.tar.gz',timeout=40).read()
    (root/(repo+'-APKINDEX.tar.gz')).write_bytes(raw)
    with tarfile.open(fileobj=io.BytesIO(raw)) as tar:text=tar.extractfile('APKINDEX').read().decode()
    for paragraph in text.split('\n\n'):
        d=dict(line.split(':',1) for line in paragraph.splitlines() if ':' in line)
        if 'P' in d:packages[d['P']]=(repo,d)
names=['dbus-dev','libgudev-dev','eudev-dev','elogind-dev','polkit-dev']
report=[]
for name in names:
    repo,p=packages[name];filename=name+'-'+p['V']+'.apk';url=base+repo+'/aarch64/'+filename
    data=urllib.request.urlopen(url,timeout=45).read();(root/filename).write_bytes(data)
    report.append(dict(package=name,version=p['V'],url=url,sha256=hashlib.sha256(data).hexdigest(),depends=p.get('D','')))
(root/'download-manifest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
