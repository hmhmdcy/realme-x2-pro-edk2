"""Transport for the observed unexpected reboot; old267 guards stay historical."""
from pathlib import Path
import importlib.util,json
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel269')
spec=importlib.util.spec_from_file_location('transport267',Path(__file__).resolve().parents[1]/'kernel267/host.py')
transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)
def ssh(command,**kwargs):
 expected=json.loads((PRIVATE/'current-boot-private.json').read_text())['boot_id']
 q=transport.raw_ssh('cat /proc/sys/kernel/random/boot_id',timeout=15)
 assert q.stdout.decode().strip()==expected,'Boot changed: inspect crash records before adopting another identity'
 return transport.raw_ssh(command,**kwargs)
