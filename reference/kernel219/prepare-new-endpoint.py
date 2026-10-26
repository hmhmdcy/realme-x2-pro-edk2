from pathlib import Path
import json,shutil
p=Path('/mnt/e/edk2-samurai-out/kernel219');assert json.loads((p/'flash-validation.json').read_text())['boot_flash_success'] and (p/'fastboot-reboot-request-private.json').exists()
old=p/'usb-ipv6-candidates-private.json';backup=p/'usb-ipv6-before-newboot-private.json';assert old.exists() and not backup.exists();shutil.move(old,backup)
print('Old211 endpoint preserved; fresh new-boot USB discovery required.')
