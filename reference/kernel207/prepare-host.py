from pathlib import Path
import os, shutil
os.umask(0o077)
out = Path('/mnt/e/edk2-samurai-out/kernel207')
out.mkdir(mode=0o700)
shutil.copyfile(out.parent / 'kernel206/usb-ipv6-candidates-private.json', out / 'usb-ipv6-candidates-private.json')
here = Path(__file__).resolve().parent
for name in ['host.py', 'run-native.py']:
    (here / name).write_text((here.parent / 'kernel206' / name).read_text().replace('kernel206', 'kernel207').replace('Stage206', 'Stage207'))
print('207 strict-key endpoint and private evidence directory prepared; native boot guard remains required.')
