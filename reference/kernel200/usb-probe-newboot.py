from pathlib import Path
import importlib.util,json,subprocess

ref=Path(__file__).resolve().parent;out=Path('/mnt/e/edk2-samurai-out/kernel200')
spec=importlib.util.spec_from_file_location('usb188',ref.parent/'kernel188/host.py');usb=importlib.util.module_from_spec(spec);spec.loader.exec_module(usb);usb.PRIVATE=out
try:p=usb.ssh('python3 -',input=(ref/'collect-newboot.py').read_bytes(),timeout=100)
except subprocess.CalledProcessError as error:
 (out/'usb-newboot-failed-private.log').write_bytes((error.stdout or b'')+(error.stderr or b''));raise SystemExit('Fresh USB probe failed; private evidence retained; no transition repeated')
(out/'runtime-private.json').write_bytes(p.stdout);r=json.loads(p.stdout)
assert r['new_boot_identity_verified'];(ref/'runtime-validation.json').write_text(json.dumps(r,indent=2)+'\n')
usb.download('/var/lib/samurai/k200-runtime/boot-id-private.txt',out/'new-boot-id-private.txt')
# Keep the old Wi-Fi implementation available, while using the newly verified USB peer for this boot.
backup=ref/'host-before-newboot.py'
if not backup.exists():backup.write_bytes((ref/'host.py').read_bytes())
(ref/'host.py').write_text('''from pathlib import Path
import importlib.util,subprocess
spec=importlib.util.spec_from_file_location('usb188',Path(__file__).resolve().parent.parent/'kernel188/host.py');transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel200');transport.PRIVATE=PRIVATE
def call(method,*args,**kwargs):
 try:return method(*args,**kwargs)
 except subprocess.CalledProcessError as error:
  (PRIVATE/'transport-last-failure-private.log').write_bytes((error.stdout or b'')+(error.stderr or b''));raise RuntimeError('Authenticated USB operation failed; private details retained') from None
def ssh(command,*,input=None,timeout=60):return call(transport.ssh,command,input=input,timeout=timeout)
def upload(path,destination):return call(transport.upload,path,destination)
def download(source,destination):return call(transport.download,source,destination)
''')
print(json.dumps(r))
