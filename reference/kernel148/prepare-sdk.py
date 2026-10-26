from pathlib import Path
import os,subprocess,json
os.umask(0o077)
apks=Path('/var/lib/samurai/k148-sdk-apks'); sdk=Path('/tmp/k148-sdk')
sdk.mkdir(mode=0o755,exist_ok=False)
with (apks / 'extract-private.log').open('wb') as f:
    for apk in sorted(apks.glob('*.apk')):
        subprocess.run(['apk','verify',str(apk)],stdout=f,stderr=subprocess.STDOUT,check=True)
        subprocess.run(['apk','extract','--destination',str(sdk),str(apk)],stdout=f,stderr=subprocess.STDOUT,check=True)
subprocess.run(['sha256sum','-c',str(apks / 'packages-before.sha256')],check=True)
env=dict(os.environ,PATH=str(sdk / 'usr/bin')+':'+os.environ['PATH'],LD_LIBRARY_PATH=str(sdk / 'usr/lib')+':'+str(sdk / 'lib'),GCC_EXEC_PREFIX=str(sdk / 'usr/lib/gcc')+'/')
with (apks / 'compiler-private.log').open('wb') as f:
    subprocess.run([str(sdk / 'usr/bin/gcc'),'--version'],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
print('K148_SIGNED_SDK_EXTRACTED_WITHOUT_PACKAGE_INSTALLATION')
