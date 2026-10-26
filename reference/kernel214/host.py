from pathlib import Path
import importlib.util,subprocess
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel214')
spec=importlib.util.spec_from_file_location('strict_usb214',Path(__file__).resolve().parent.parent/'kernel188/host.py');transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport);transport.PRIVATE=PRIVATE
def call(method,*args,**kwargs):
    try:return method(*args,**kwargs)
    except (subprocess.CalledProcessError,subprocess.TimeoutExpired) as error:
        (PRIVATE/'transport-last-failure-private.log').write_bytes((error.stdout or b'')+(error.stderr or b''));raise RuntimeError('Authenticated214 transport failed; diagnostics retained privately') from None
def ssh(command,*,input=None,timeout=60):return call(transport.ssh,command,input=input,timeout=timeout)
def upload(path,destination):return call(transport.upload,path,destination)
def download(source,destination):return call(transport.download,source,destination)
