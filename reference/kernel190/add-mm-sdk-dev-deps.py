from pathlib import Path
import hashlib,json,subprocess
out=Path('/var/lib/samurai/k190-mm-build');sdk=Path('/var/lib/samurai/k190-mm-sdk');db=Path('/lib/apk/db/installed').read_bytes()
packages=sorted(Path('/var/lib/samurai/k190-mm-sdk-host-apks').glob('*.apk'));assert len(packages)==5
for i,p in enumerate(packages):
 with (out/('extra-verify-'+str(i)+'-private.log')).open('wb') as log:subprocess.run(['apk','verify',str(p)],stdout=log,stderr=subprocess.STDOUT,check=True)
 with (out/('extra-extract-'+str(i)+'-private.log')).open('wb') as log:subprocess.run(['apk','extract','--force-overwrite','--destination',str(sdk),str(p)],stdout=log,stderr=subprocess.STDOUT,check=True)
for name in ['libgudev-1.0.so.0','libudev.so.1','libelogind.so.0','libpolkit-gobject-1.so.0','libdbus-1.so.3']:
 original=Path('/usr/lib')/name;assert original.is_file()
 for dest in {sdk/'usr/lib'/name,sdk/'usr/lib'/original.resolve().name}:
  if dest.is_symlink():dest.unlink()
  dest.write_bytes(original.read_bytes())
assert Path('/lib/apk/db/installed').read_bytes()==db
print('5 additional signed development APKs extracted; runtime libraries preserved; package database unchanged')
