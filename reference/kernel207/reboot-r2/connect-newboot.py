from pathlib import Path
import importlib.util, json, subprocess

here = Path(__file__).resolve().parent
private = Path('/mnt/e/edk2-samurai-out/kernel207/reboot-r2')
spec = importlib.util.spec_from_file_location('usb188', here.parent.parent/'kernel188/host.py')
usb = importlib.util.module_from_spec(spec); spec.loader.exec_module(usb); usb.PRIVATE = private
try:
    result = usb.ssh('python3 -', input=(here/'collect-newboot.py').read_bytes(), timeout=200)
except subprocess.CalledProcessError as error:
    (private/'newboot-probe-failed-private.log').write_bytes((error.stdout or b'')+(error.stderr or b''))
    raise SystemExit('New boot probe failed; inspect state without repeating transition')
report = json.loads(result.stdout)
assert report['new_boot_identity_verified']
(private/'runtime-private.json').write_bytes(result.stdout)
(here/'runtime-validation.json').write_text(json.dumps(report, indent=2)+'\n')
usb.download('/var/lib/samurai/k207r2-runtime/boot-id-private.txt', private/'new-boot-id-private.txt')
backup = here/'host-before-newboot.py'
assert not backup.exists()
backup.write_bytes((here/'host.py').read_bytes())
(here/'host.py').write_text('''from pathlib import Path
import importlib.util,subprocess
spec=importlib.util.spec_from_file_location('usb188',Path(__file__).resolve().parent.parent.parent/'kernel188/host.py');transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel207/reboot-r2');transport.PRIVATE=PRIVATE
def call(method,*args,**kwargs):
 try:return method(*args,**kwargs)
 except subprocess.CalledProcessError as error:
  (PRIVATE/'transport-last-failure-private.log').write_bytes((error.stdout or b'')+(error.stderr or b''));raise RuntimeError('Authenticated USB operation failed; private details retained') from None
def ssh(command,*,input=None,timeout=60):return call(transport.ssh,command,input=input,timeout=timeout)
def upload(path,destination):return call(transport.upload,path,destination)
def download(source,destination):return call(transport.download,source,destination)
''')
print(json.dumps(report))
