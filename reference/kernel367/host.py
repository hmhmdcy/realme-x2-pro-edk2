from pathlib import Path
import importlib.util,json,shlex
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel367');PRIVATE.mkdir(mode=0o700,exist_ok=True)
spec=importlib.util.spec_from_file_location('host366',Path(__file__).resolve().parents[1]/'kernel366/host.py')
previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
usb_spec=importlib.util.spec_from_file_location('usb360',Path(__file__).resolve().parents[1]/'kernel360/host.py')
usb=importlib.util.module_from_spec(usb_spec);usb_spec.loader.exec_module(usb)
raw_ssh=usb.raw_ssh
def ssh(command,**kwargs):
    adoption=PRIVATE/'postboot-adoption-private.json'
    if not adoption.exists():adoption=PRIVATE.parent/'kernel366/recovered-boot-adoption-private.json'
    guard=json.loads(adoption.read_text())['guard_path']
    raw_ssh('cmp -s /proc/sys/kernel/random/boot_id '+shlex.quote(guard),timeout=15)
    return raw_ssh(command,**kwargs)
