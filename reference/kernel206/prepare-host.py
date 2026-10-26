from pathlib import Path
import os, shutil
os.umask(0o077)
out = Path('/mnt/e/edk2-samurai-out/kernel206')
out.mkdir(mode=0o700)
shutil.copyfile(out.parent / 'kernel205/reboot-r2/usb-ipv6-candidates-private.json', out / 'usb-ipv6-candidates-private.json')
print('206 private output prepared from last verified endpoint; native actions require the current r2 boot guard.')
