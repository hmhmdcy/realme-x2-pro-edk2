from pathlib import Path
import json,tarfile

out=Path('/mnt/e/edk2-samurai-out/kernel203');result=[]
for path in (out/'upstream-apks').glob('*.apk'):
 with tarfile.open(path,'r:gz',ignore_zeros=True) as archive:
  raw=archive.extractfile('.PKGINFO').read().decode();(out/(path.name+'-pkginfo-inspection.txt')).write_text(raw)
  result.append(dict(file=path.name,pkginfo_fields=[line for line in raw.splitlines() if line.startswith(('pkgname = ','pkgver = ','arch = '))]))
print(json.dumps(result))
