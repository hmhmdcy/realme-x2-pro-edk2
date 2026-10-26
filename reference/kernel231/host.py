"""Strict transport for same-boot231 file-service evidence, boot230 guard."""
from pathlib import Path
import importlib.util,subprocess
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel231');PRIVATE.mkdir(exist_ok=True)
spec=importlib.util.spec_from_file_location('usb188',Path(__file__).resolve().parent.parent/'kernel188/host.py')
transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport);transport.PRIVATE=PRIVATE
def call(fn,*args,**kwargs):
 try:return fn(*args,**kwargs)
 except (subprocess.CalledProcessError,subprocess.TimeoutExpired) as error:
  (PRIVATE/'transport-last-failure-private.log').write_bytes((error.stdout or b'')+(error.stderr or b''))
  raise RuntimeError('Authenticated231 operation failed; inspect existing operation and private diagnostics') from None
def ssh(command,*,input=None,timeout=60):return call(transport.ssh,command,input=input,timeout=timeout)
def upload(source,destination):return call(transport.upload,source,destination)
