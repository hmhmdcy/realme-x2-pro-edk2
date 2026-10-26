from pathlib import Path
import re
p=Path('/mnt/e/edk2-samurai-out/kernel201/test-geoclue-gnss-failed-private.log')
s=p.read_text(errors='replace');s=re.sub(r'\b(?:\d{1,3}\.){3}\d{1,3}\b','<private-ip>',s);s=re.sub(r'fe80:[0-9a-fA-F:%]+','<private-usb-peer>',s)
print(s[-2200:])
