from pathlib import Path
import re
s=Path('/mnt/e/edk2-samurai-out/kernel200/transport-last-failure-private.log').read_text(errors='replace')
s=re.sub(r'\b(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}\b','<private-mac>',s)
s=re.sub(r'\b(?:\d{1,3}\.){3}\d{1,3}\b','<private-ip>',s)
s=re.sub(r'\b[0-9a-f]{8}-[0-9a-f-]{27,}\b','<private-boot-id>',s)
print(s[-1600:])
