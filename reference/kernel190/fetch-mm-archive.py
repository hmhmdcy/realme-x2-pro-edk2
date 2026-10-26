from pathlib import Path
import hashlib,json,re,tarfile,urllib.request

ref=Path(__file__).resolve().parent;root=Path('/mnt/e/edk2-samurai-out/kernel190/mm-build');root.mkdir(exist_ok=True)
record=json.loads((ref/'location-source-reference.json').read_text());commit=record['modemmanager_commit']
recipe=Path('/mnt/e/edk2-samurai-out/kernel190/location-sources/APKBUILD').read_text()
name='ModemManager-'+commit+'.tar.gz';expected=re.search(r'([0-9a-f]{128})\s+'+re.escape(name),recipe)[1]
url='https://distfiles.alpinelinux.org/distfiles/edge/'+name
raw=urllib.request.urlopen(url,timeout=40).read();assert hashlib.sha512(raw).hexdigest()==expected
path=root/name;path.write_bytes(raw)
with tarfile.open(path) as tar:tar.extractall(root,filter='data')
source=next(p for p in root.iterdir() if p.is_dir())
assert hashlib.sha256((source/'src/mm-shared-qmi.c').read_bytes()).hexdigest()==next(i['sha256'] for i in record['sources'] if i['path']=='src/mm-shared-qmi.c')
report=dict(url=url,commit=commit,archive_sha256=hashlib.sha256(raw).hexdigest(),apkbuild_sha512_verified=True,source_directory=source.name)
(ref/'mm-source-archive-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
