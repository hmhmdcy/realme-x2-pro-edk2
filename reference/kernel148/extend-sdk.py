from pathlib import Path
import os,subprocess
os.umask(0o077); apks=Path('/var/lib/samurai/k148-sdk-apks'); sdk=Path('/tmp/k148-sdk')
assert (sdk/'usr/bin/gcc').exists()
with (apks/'build-extract-private.log').open('wb') as f:
    for p in sorted(apks.glob('*.apk')):
        subprocess.run(['apk','verify',str(p)],stdout=f,stderr=subprocess.STDOUT,check=True)
        subprocess.run(['apk','extract','--force-overwrite','--destination',str(sdk),str(p)],stdout=f,stderr=subprocess.STDOUT,check=True)
subprocess.run(['sha256sum','-c',str(apks/'packages-before.sha256')],check=True)
print('K148_SIGNED_BUILD_SDK_EXTRACTED_PACKAGE_DB_UNCHANGED')
