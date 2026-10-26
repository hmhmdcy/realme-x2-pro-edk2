from pathlib import Path
import os,shutil
os.umask(0o077);out=Path('/mnt/e/edk2-samurai-out/kernel205');out.mkdir(mode=0o700,exist_ok=True)
target=out/'usb-ipv6-candidates-private.json';assert not target.exists();shutil.copyfile(out.parent/'kernel204/reboot-r2/usb-ipv6-candidates-private.json',target)
print('Copied last verified scoped USB endpoint privately; a fresh device boot guard is still required.')
