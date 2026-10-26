from pathlib import Path
import host,subprocess
root=Path('/mnt/e/edk2-samurai-out/kernel190/mm-build');name='ModemManager-7f0bf17ab518cd78925cf7e53cc0d5c42f88b41a'
try:
 host.upload(root/(name+'.tar.gz'),'/var/lib/samurai/k190-mm-build/source.tar.gz')
 host.upload(root/name/'src/mm-shared-qmi.c','/var/lib/samurai/k190-mm-build/mm-shared-qmi-patched.c')
except subprocess.CalledProcessError as error:
 (host.PRIVATE/'stage-mm-source-failure-private.log').write_bytes(error.stdout+error.stderr);raise SystemExit('Source upload failed; private log retained')
print('Verified archive and patched source staged')
