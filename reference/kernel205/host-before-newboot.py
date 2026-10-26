from pathlib import Path
import importlib.util,subprocess,time

spec=importlib.util.spec_from_file_location('current_usb',Path(__file__).resolve().parent.parent/'kernel188/host.py')
transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel205');PRIVATE.mkdir(mode=0o700,exist_ok=True);transport.PRIVATE=PRIVATE
def call(method,*args,**kwargs):
 try:return method(*args,**kwargs)
 except (subprocess.CalledProcessError,subprocess.TimeoutExpired) as error:
  (PRIVATE/('transport-failure-'+str(time.time_ns())+'-private.log')).write_bytes((error.stdout or b'')+(error.stderr or b''));raise RuntimeError('Authenticated current USB operation failed; timestamped private output retained') from None
def ssh(command,*,input=None,timeout=60):return call(transport.ssh,command,input=input,timeout=timeout)
def upload(path,destination):return call(transport.upload,path,destination)
def download(source,destination):return call(transport.download,source,destination)
