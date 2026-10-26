from pathlib import Path
import hashlib,json,urllib.request

out=Path('/mnt/e/edk2-samurai-out/kernel203/package-docs');out.mkdir(mode=0o700,exist_ok=True)
base='https://raw.githubusercontent.com/alpinelinux/apk-tools/v3.0.8/'
report=[]
for name in ['doc/apk-mkpkg.8.scd','doc/apk-adbsign.8.scd','src/app_mkpkg.c']:
    with urllib.request.urlopen(base+name,timeout=25) as response:data=response.read(1024*1024)
    (out/Path(name).name).write_bytes(data)
    report.append(dict(url=base+name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
print(json.dumps(report))
