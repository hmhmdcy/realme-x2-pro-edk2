from pathlib import Path
import json
private=Path('/mnt/e/edk2-samurai-out/kernel212')
assert json.loads((private/'fastboot-reboot-private.json').read_text())['request_count']==1
old=private/'usb-ipv6-candidates-private.json';backup=private/'usb-ipv6-before-newboot-private.json'
assert old.exists() and not backup.exists();old.rename(backup)
print('212 old USB endpoint preserved; rediscover the new peer before authentication.')
