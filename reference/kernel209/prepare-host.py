from pathlib import Path
import os,shutil
os.umask(0o077)
here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel209')
private.mkdir(mode=0o700)
shutil.copyfile(private.parent/'kernel208/usb-ipv6-candidates-private.json',private/'usb-ipv6-candidates-private.json')
(here/'host.py').write_text((here.parent/'kernel208/host.py').read_text().replace("Path('/mnt/e/edk2-samurai-out/kernel208')","Path('/mnt/e/edk2-samurai-out/kernel209')"))
(here/'run-native.py').write_bytes((here.parent/'kernel208/run-native.py').read_bytes())
# Keep the current208 guard; only the newly created output directory changes.
source=(here.parent/'kernel208/baseline.py').read_text().replace('k207r2-runtime','k208-baseline').replace("out = root / 'k208-baseline'", "out = root / 'k209-baseline'").replace('stage=208','stage=209')
(here/'baseline.py').write_text(source)
print('209 endpoint prepared from verified208 transport; native boot guard still required.')
