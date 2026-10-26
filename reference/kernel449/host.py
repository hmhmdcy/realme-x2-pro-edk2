from pathlib import Path
import importlib.util,json,shlex
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel449');PRIVATE.mkdir(mode=0o700,exist_ok=True)
s=importlib.util.spec_from_file_location('host448',Path(__file__).resolve().parents[1]/'kernel448/host.py');old=importlib.util.module_from_spec(s);s.loader.exec_module(old)
raw_ssh=old.raw_ssh
def ssh(command,**kwargs):
 adoption=json.loads((PRIVATE/'boot-adoption-private.json').read_text())
 assert adoption['original_key_verified'] and adoption['baseline440_verified']
 raw_ssh('cmp -s /proc/sys/kernel/random/boot_id '+shlex.quote(adoption['guard_path']),timeout=15).check_returncode()
 return raw_ssh(command,**kwargs)
