from pathlib import Path
import subprocess
out=Path('/var/lib/samurai/k190-mm-build');sdk=Path('/var/lib/samurai/k190-mm-sdk');db=Path('/lib/apk/db/installed').read_bytes()
for p in Path('/var/lib/samurai/k190-mm-sdk-host-apks').glob('*.apk'):
 if not p.name.startswith(('gettext-','libxml2-','libunistring-')):continue
 with (out/('msgfmt-'+p.name+'-private.log')).open('wb') as log:
  subprocess.run(['apk','verify',str(p)],stdout=log,stderr=subprocess.STDOUT,check=True)
  subprocess.run(['apk','extract','--force-overwrite','--destination',str(sdk),str(p)],stdout=log,stderr=subprocess.STDOUT,check=True)
assert Path('/lib/apk/db/installed').read_bytes()==db
print('Signed gettext tools extracted into isolated SDK')
