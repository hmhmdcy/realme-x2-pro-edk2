"""Use the authenticated current endpoint; stage190 evidence remains private."""
from pathlib import Path
import importlib.util
import subprocess
import ipaddress,json

spec=importlib.util.spec_from_file_location('transport189r2',Path(__file__).resolve().parent.parent/'kernel189/reboot-r2/host.py')
transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel190');PRIVATE.mkdir(exist_ok=True)

class PrivateTransportError(subprocess.CalledProcessError):
    def __str__(self):
        return 'Authenticated transport failed; details retained privately (exit %s)' % self.returncode

def _private_call(method,*args,**kwargs):
    try:return method(*args,**kwargs)
    except subprocess.CalledProcessError as error:
        (PRIVATE/'transport-last-failure-private.log').write_bytes((error.stdout or b'')+(error.stderr or b''))
        raise PrivateTransportError(error.returncode,method.__name__,output=error.stdout,stderr=error.stderr) from None

def _wifi():
    path=PRIVATE/'wifi-current-endpoint-private.json'
    if not path.exists():return None
    address=json.loads(path.read_text())['IPAddress']
    ip=ipaddress.ip_address(address);assert ip.version==4 and ip.is_private and not ip.is_loopback
    base=transport.parent.transport.base_transport()
    return base,address

def ssh(command,*,input=None,timeout=60):
    link=_wifi()
    if link is None:return _private_call(transport.ssh,command,input=input,timeout=timeout)
    base,address=link
    return _private_call(subprocess.run,[base.SSH,'-T',*base.OPTIONS,'-4','-o','HostKeyAlias=169.254.42.1','root@'+address,command],input=input,capture_output=True,timeout=timeout,check=True)

def upload(path,destination):
    link=_wifi()
    if link is None:return _private_call(transport.upload,path,destination)
    base,address=link;path=Path(path).resolve();assert str(path).startswith('/mnt/e/')
    windows='E:/'+str(path)[len('/mnt/e/'):]
    return _private_call(subprocess.run,[base.SCP,'-O',*base.OPTIONS,'-4','-o','HostKeyAlias=169.254.42.1',windows,'root@'+address+':'+destination],capture_output=True,timeout=120,check=True)

def download(source,destination):
    link=_wifi()
    if link is None:return _private_call(transport.download,source,destination)
    base,address=link;destination=Path(destination).resolve();assert str(destination).startswith('/mnt/e/edk2-samurai-out/')
    windows='E:/'+str(destination)[len('/mnt/e/'):]
    return _private_call(subprocess.run,[base.SCP,'-O',*base.OPTIONS,'-4','-o','HostKeyAlias=169.254.42.1','root@'+address+':'+source,windows],capture_output=True,timeout=180,check=True)
