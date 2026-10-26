from pathlib import Path
import subprocess
root=Path('/var/lib/samurai/k190-mm-build');sdk=Path('/var/lib/samurai/k190-mm-sdk');db=Path('/lib/apk/db/installed').read_bytes()
p=next(Path('/var/lib/samurai/k190-mm-sdk-host-apks').glob('gettext-dev-*.apk'))
with (root/'gettext-dev-extract-private.log').open('wb') as log:
 subprocess.run(['apk','verify',str(p)],stdout=log,stderr=subprocess.STDOUT,check=True)
 subprocess.run(['apk','extract','--force-overwrite','--destination',str(sdk),str(p)],stdout=log,stderr=subprocess.STDOUT,check=True)
assert (sdk/'usr/include/libintl.h').is_file()
assert Path('/lib/apk/db/installed').read_bytes()==db
print('Verified gettext headers added to SDK')
