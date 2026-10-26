from pathlib import Path
import importlib.util,json,shlex
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel363');PRIVATE.mkdir(mode=0o700,exist_ok=True)
spec=importlib.util.spec_from_file_location('host362',Path(__file__).resolve().parents[1]/'kernel362/host.py')
previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
raw_ssh=previous.raw_ssh
def ssh(command,**kwargs):
    adopted=PRIVATE/'postboot-adoption-private.json'
    if not adopted.exists():return previous.ssh(command,**kwargs)
    guard=json.loads(adopted.read_text())['guard_path']
    raw_ssh('cmp -s /proc/sys/kernel/random/boot_id '+shlex.quote(guard),timeout=15)
    return raw_ssh(command,**kwargs)
