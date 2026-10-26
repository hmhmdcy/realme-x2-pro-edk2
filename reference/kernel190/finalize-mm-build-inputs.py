from pathlib import Path
import hashlib,json,re,urllib.request
import host
ref=Path(__file__).resolve().parent;root=host.PRIVATE
name='0001-intel-XMM7360-fix-big-endian-handling-of-ASN-integer.patch'
recipe=(root/'location-sources/APKBUILD').read_text();expected=re.search(r'([0-9a-f]{128})\s+'+re.escape(name),recipe)[1]
url='https://raw.githubusercontent.com/alpinelinux/aports/master/community/modemmanager/'+name
data=urllib.request.urlopen(url,timeout=30).read();assert hashlib.sha512(data).hexdigest()==expected
(root/name).write_bytes(data);host.upload(root/name,'/var/lib/samurai/k190-mm-build/'+name)
record=json.loads((ref/'mm-patch-validation.json').read_text())
path=ref/'build-mm.py';text=path.read_text();assert 'PATCHED_SOURCE_HASH' in text
text=text.replace('PATCHED_SOURCE_HASH',record['patched_sha256'])
text=text.replace("source=next(destination.iterdir())", "source=next(destination.iterdir())\nsubprocess.run(['patch','-d',str(source),'-p1','-i',str(out/'"+name+"')],check=True,capture_output=True)")
path.write_text(text)
(ref/'mm-distro-patch-validation.json').write_text(json.dumps(dict(url=url,apkbuild_sha512_verified=True,sha256=hashlib.sha256(data).hexdigest()),indent=2)+'\n')
print('Pinned source hash and Alpine distribution patch preserved')
