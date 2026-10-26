from pathlib import Path
import urllib.request

root=Path('/mnt/e/edk2-samurai-out/kernel203/package-docs')
for name in ['apk-mkndx.8.scd','apk-repositories.5.scd']:
 with urllib.request.urlopen('https://raw.githubusercontent.com/alpinelinux/apk-tools/v3.0.8/doc/'+name,timeout=25) as response:data=response.read(100000)
 (root/name).write_bytes(data)
print('Read the matching3.0.8 repository/index reference; no scripts executed.')
