from pathlib import Path
import importlib.util,json,shlex
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel375');PRIVATE.mkdir(mode=0o700,exist_ok=True)
spec=importlib.util.spec_from_file_location('host374',Path(__file__).resolve().parents[1]/'kernel374/host.py')
previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
raw_ssh=previous.raw_ssh

def ssh(command,**kwargs):
 adoption=PRIVATE/'recovered-boot-adoption-private.json'
 if not adoption.exists():return previous.ssh(command,**kwargs)
 raw_ssh('cmp -s /proc/sys/kernel/random/boot_id '+shlex.quote(json.loads(adoption.read_text())['guard_path']),timeout=15)
 return raw_ssh(command,**kwargs)
