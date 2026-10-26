from pathlib import Path
import hashlib,json,urllib.request
out=Path('/mnt/e/edk2-samurai-out/kernel197');out.mkdir(exist_ok=True);files=[]
for name in ['v4l-utils-libs','v4l-utils']:
 filename=name+'-1.32.0-r1.apk';url='https://dl-cdn.alpinelinux.org/alpine/edge/community/aarch64/'+filename
 with urllib.request.urlopen(url,timeout=45) as response:data=response.read()
 assert len(data)>10000;dest=out/filename;assert not dest.exists();dest.write_bytes(data);files.append(dict(file=filename,url=url,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
(out/'video-package-download-private.json').write_text(json.dumps(files,indent=2)+'\n');print(json.dumps(files))
