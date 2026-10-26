from pathlib import Path
import importlib.util,json,subprocess
spec=importlib.util.spec_from_file_location('usb188',Path(__file__).resolve().parent.parent/'kernel188/host.py');transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel213');transport.PRIVATE=PRIVATE
def call(method,*args,**kwargs):
 try:return method(*args,**kwargs)
 except (subprocess.CalledProcessError,subprocess.TimeoutExpired) as error:
  (PRIVATE/'transport-last-failure-private.log').write_bytes((error.stdout or b'')+(error.stderr or b''));raise RuntimeError('Authenticated transport operation failed; private details retained') from None
def selected():
 record=PRIVATE/'selected-transport-private.json'
 if not record.exists():return transport
 choice=json.loads(record.read_text());assert choice['kind']=='wifi' and choice['current213_guard_verified'] and choice['strict_original_key_verified']
 spec=importlib.util.spec_from_file_location('wifi213',Path(__file__).resolve().parent.parent/'kernel200/host-before-newboot.py');wifi=importlib.util.module_from_spec(spec);spec.loader.exec_module(wifi);return wifi
def ssh(command,*,input=None,timeout=60):return call(selected().ssh,command,input=input,timeout=timeout)
def upload(path,destination):return call(selected().upload,path,destination)
def download(source,destination):return call(selected().download,source,destination)
