from pathlib import Path
import json,shutil
private=Path('/mnt/e/edk2-samurai-out/kernel210')
assert json.loads((private/'flash-validation.json').read_text())['boot_flash_success']
old=private/'usb-ipv6-candidates-private.json';backup=private/'usb-ipv6-before-newboot-private.json'
assert old.exists() and not backup.exists();shutil.move(old,backup)
print('Prior USB endpoint preserved; fresh new-boot discovery required.')
