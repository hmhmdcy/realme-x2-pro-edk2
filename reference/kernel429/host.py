from pathlib import Path
import importlib.util,json,shlex
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel429');PRIVATE.mkdir(mode=0o700,exist_ok=True)
s=importlib.util.spec_from_file_location('host428',Path(__file__).resolve().parents[1]/'kernel428/host.py');old=importlib.util.module_from_spec(s);s.loader.exec_module(old)
raw_ssh=old.raw_ssh
def ssh(command,**kwargs):
 adoption=PRIVATE/'postboot-adoption-private.json'
 if not adoption.exists():return old.ssh(command,**kwargs)
 guard=json.loads(adoption.read_text())['guard_path']
 q=raw_ssh('cmp -s /proc/sys/kernel/random/boot_id '+shlex.quote(guard),timeout=15);q.check_returncode()
 return raw_ssh(command,**kwargs)
