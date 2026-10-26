from pathlib import Path
import hashlib,json,urllib.request

out=Path('/mnt/e/edk2-samurai-out/kernel203');root=Path('/home/cy122/pmos-samurai-rootfs01/work')
matches=[]
for directory in ['cache_apk_aarch64','cache_apk_x86_64','packages']:
    for path in (root/directory).rglob('modemmanager*.apk'):
        matches.append(dict(path=str(path),bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
(out/'package-cache-private.json').write_text(json.dumps(matches,indent=2)+'\n')
print(json.dumps(matches))
url='https://raw.githubusercontent.com/alpinelinux/apk-tools/v3.0.8/doc/apk-package.5.scd'
with urllib.request.urlopen(url,timeout=25) as response:data=response.read(100000)
(out/'package-docs/apk-package.5.scd').write_bytes(data)
print(json.dumps(dict(package_metadata_reference=url,bytes=len(data))))
