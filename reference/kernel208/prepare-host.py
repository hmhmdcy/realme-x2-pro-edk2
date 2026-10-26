from pathlib import Path
import os,shutil

os.umask(0o077)
here=Path(__file__).resolve().parent
private=Path('/mnt/e/edk2-samurai-out/kernel208')
private.mkdir(mode=0o700)
shutil.copyfile(private.parent/'kernel207/reboot-r2/usb-ipv6-candidates-private.json',private/'usb-ipv6-candidates-private.json')
(here/'host.py').write_text((here.parent/'kernel207/host.py').read_text().replace("Path('/mnt/e/edk2-samurai-out/kernel207')","Path('/mnt/e/edk2-samurai-out/kernel208')"))
(here/'run-native.py').write_bytes((here.parent/'kernel207/run-native.py').read_bytes())
source=(here.parent/'kernel207/baseline.py').read_text()
source=source.replace('k205r2-runtime','k207r2-runtime').replace('k207-baseline','k208-baseline').replace('stage=207','stage=208').replace('same205_r2_boot_verified','same207_r2_boot_verified').replace('production_tftp206_exact','production_tftp207_exact')
source=source.replace('d0906a5abb939fa5d1e906692b0ac769f0760857d4a9780a07ad5b59d1c4ca4e','b3bb82b9d090a5d06e9ba2ca24e3373ab1c1e7cc2a5c6b603e2acb02715487a1')
source=source.replace('ffb65d31b337fbdad89ff9c575b133574756121f75cd2967da10f1028c1b5fbd','854c9a8c787d68ccefc998064983f3aa67141fe94def27f4dde87925bd18f24f')
(here/'baseline.py').write_text(source)
print('208 endpoint prepared from current207 secondboot. Native identity verification pending.')
