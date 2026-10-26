from pathlib import Path
import importlib.util,json
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel365');PRIVATE.mkdir(mode=0o700,exist_ok=True)
spec=importlib.util.spec_from_file_location('host364',Path(__file__).resolve().parents[1]/'kernel364/host.py')
previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
raw_ssh=previous.raw_ssh
def ssh(command,**kwargs):
    adoption=PRIVATE/'postboot-adoption-private.json'
    if not adoption.exists():return previous.ssh(command,**kwargs)
    import shlex
    guard=json.loads(adoption.read_text())['guard_path']
    return raw_ssh('cmp -s /proc/sys/kernel/random/boot_id '+shlex.quote(guard)+' && '+command,**kwargs)
