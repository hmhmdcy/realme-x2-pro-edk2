"""Preserve deployed275 boot guard while preparing the CCI I/O candidate."""
from pathlib import Path
import importlib.util,json,types
spec=importlib.util.spec_from_file_location('camera275_transport',Path(__file__).resolve().parents[1]/'kernel275/host.py')
previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel276');PRIVATE.mkdir(mode=0o700,exist_ok=True)
_fresh_raw=types.FunctionType(previous._fresh_raw.__code__,dict(previous._fresh_raw.__globals__,PRIVATE=PRIVATE))
def raw_ssh(command,**kwargs):
 if (PRIVATE/'usb-ipv6-candidates-private.json').exists():return _fresh_raw(command,**kwargs)
 return previous.raw_ssh(command,**kwargs)
def ssh(command,**kwargs):
 identity=PRIVATE/'postboot-verified-private.json'
 if not identity.exists():return previous.ssh(command,**kwargs)
 expected=json.loads(identity.read_text())['boot_id']
 assert raw_ssh('cat /proc/sys/kernel/random/boot_id',timeout=15).stdout.decode().strip()==expected,'Boot changed; inspect actual state before any operation'
 return raw_ssh(command,**kwargs)
