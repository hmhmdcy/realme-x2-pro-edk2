from pathlib import Path
import importlib.util,subprocess

spec=importlib.util.spec_from_file_location('current_verified_wifi',Path(__file__).resolve().parent.parent/'kernel200/host-before-newboot.py')
transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel203');PRIVATE.mkdir(mode=0o700,exist_ok=True)
class PrivateTransportError(subprocess.CalledProcessError):
 def __init__(self,error):super().__init__(error.returncode,'authenticated current Wi-Fi operation',output=error.stdout,stderr=error.stderr)
def call(method,*args,**kwargs):
 try:return method(*args,**kwargs)
 except subprocess.CalledProcessError as error:
  (PRIVATE/'transport-last-failure-private.log').write_bytes((error.stdout or b'')+(error.stderr or b''));raise PrivateTransportError(error) from None
def ssh(command,*,input=None,timeout=60):return call(transport.ssh,command,input=input,timeout=timeout)
def upload(path,destination):return call(transport.upload,path,destination)
def download(source,destination):return call(transport.download,source,destination)
