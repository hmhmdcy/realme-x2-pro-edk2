"""Use the guarded deployed273 transport until a new boot is independently adopted."""
from pathlib import Path
import importlib.util,json,types
spec=importlib.util.spec_from_file_location('camera273_transport',Path(__file__).resolve().parents[1]/'kernel273/host.py')
previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel275');PRIVATE.mkdir(mode=0o700,exist_ok=True)
_fresh_raw=types.FunctionType(previous.raw_ssh.__code__,dict(previous.raw_ssh.__globals__,PRIVATE=PRIVATE))
def raw_ssh(command,**kwargs):
 if (PRIVATE/'usb-ipv6-candidates-private.json').exists():return _fresh_raw(command,**kwargs)
 return previous.raw_ssh(command,**kwargs)
def ssh(command,**kwargs):
 identity=PRIVATE/'postboot-verified-private.json'
 if not identity.exists():return previous.ssh(command,**kwargs)
 expected=json.loads(identity.read_text())['boot_id']
 assert raw_ssh('cat /proc/sys/kernel/random/boot_id',timeout=15).stdout.decode().strip()==expected,'Boot changed; inspect actual state before any operation'
 return raw_ssh(command,**kwargs)
