from pathlib import Path
r = Path('/mnt/e/RealmeX2Pro edk2')
source = (r / 'reference/kernel134/validate-usb-source.py').read_text()
source = source[:source.index("runpy.run_path(str(r / 'reference/kernel122/ensure-rootfs-volume.py'))")]
source = source.replace("/usb134'", "/usb134-r3'")
source = source.replace("host-test-private.txt", "host-test-r3-private.txt")
exec(compile(source, 'final-platform-usb-decoder-fault-check-r3', 'exec'))
