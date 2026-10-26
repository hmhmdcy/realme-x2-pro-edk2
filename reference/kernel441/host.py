from pathlib import Path
import importlib.util,json,shlex
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel441');PRIVATE.mkdir(mode=0o700,exist_ok=True)
s=importlib.util.spec_from_file_location('host440',Path(__file__).resolve().parents[1]/'kernel440/host.py');old=importlib.util.module_from_spec(s);s.loader.exec_module(old)
raw_ssh=old.raw_ssh
def ssh(command,**kwargs):
 adoption=PRIVATE/'boot-adoption-private.json'
 if not adoption.exists():return old.ssh(command,**kwargs)
 data=json.loads(adoption.read_text());assert data['original_key_verified'] and data['baseline440_verified']
 raw_ssh('cmp -s /proc/sys/kernel/random/boot_id '+shlex.quote(data['guard_path']),timeout=15).check_returncode()
 return raw_ssh(command,**kwargs)
