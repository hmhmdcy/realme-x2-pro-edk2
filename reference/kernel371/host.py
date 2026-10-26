from pathlib import Path
import importlib.util,json,shlex
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel371');PRIVATE.mkdir(mode=0o700,exist_ok=True)
spec=importlib.util.spec_from_file_location('host369',Path(__file__).resolve().parents[1]/'kernel369/host.py')
previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
def raw_ssh(command,**kwargs):
 endpoint=PRIVATE/'current-transport-private.json'
 if endpoint.exists():
  selected=json.loads(endpoint.read_text());assert selected['kind']=='usb' and selected['original_key_verified']
  spec=importlib.util.spec_from_file_location('usb360',Path(__file__).resolve().parents[1]/'kernel360/host.py')
  usb=importlib.util.module_from_spec(spec);spec.loader.exec_module(usb);return usb.raw_ssh(command,**kwargs)
 return previous.raw_ssh(command,**kwargs)

def ssh(command,**kwargs):
 adoption=PRIVATE/'recovered-boot-adoption-private.json'
 if not adoption.exists():adoption=PRIVATE.parent/'kernel369/recovered-boot-adoption-private.json'
 guard=json.loads(adoption.read_text())['guard_path'];raw_ssh('cmp -s /proc/sys/kernel/random/boot_id '+shlex.quote(guard),timeout=15)
 return raw_ssh(command,**kwargs)
