from pathlib import Path
import importlib.util,subprocess
spec=importlib.util.spec_from_file_location('usb188',Path(__file__).resolve().parent.parent/'kernel188/host.py');transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel200');transport.PRIVATE=PRIVATE
class PrivateCallError(subprocess.CalledProcessError):
 def __str__(self):return 'Private remote operation failed (exit %s); details retained privately' % self.returncode
def call(method,*args,**kwargs):
 try:return method(*args,**kwargs)
 except subprocess.CalledProcessError as error:
  (PRIVATE/'transport-last-failure-private.log').write_bytes((error.stdout or b'')+(error.stderr or b''));raise PrivateCallError(error.returncode,method.__name__,output=error.stdout,stderr=error.stderr) from None
def ssh(command,*,input=None,timeout=60):return call(transport.ssh,command,input=input,timeout=timeout)
def upload(path,destination):return call(transport.upload,path,destination)
def download(source,destination):return call(transport.download,source,destination)
