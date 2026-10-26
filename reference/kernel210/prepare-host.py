from pathlib import Path
import os,shutil
os.umask(0o077)
here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel210')
private.mkdir(mode=0o700)
shutil.copyfile(private.parent/'kernel209/usb-ipv6-candidates-private.json',private/'usb-ipv6-candidates-private.json')
(here/'host.py').write_text((here.parent/'kernel209/host.py').read_text().replace("Path('/mnt/e/edk2-samurai-out/kernel209')","Path('/mnt/e/edk2-samurai-out/kernel210')"))
(here/'run-native.py').write_bytes((here.parent/'kernel209/run-native.py').read_bytes())
source=(here.parent/'kernel209/baseline.py').read_text().replace('k208-baseline','k209-baseline').replace("out = root / 'k209-baseline'", "out = root / 'k210-baseline'").replace('stage=209','stage=210')
(here/'baseline.py').write_text(source)
print('210 transport prepared; fresh native identity check pending.')
