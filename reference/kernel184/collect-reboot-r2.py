"""Collect the second fresh kernel183 boot without mixing earlier boot evidence."""
from pathlib import Path
import subprocess
import host

ref = Path(__file__).resolve().parent
text = (ref / 'collect-reboot-runtime.py').read_text()
text = text.replace('k184-reboot-runtime', 'k184-reboot-runtime-r2')
text = text.replace('k184-preflash', 'k184r2-preflash')
result = host.ssh('python3 -', input=text.encode(), timeout=55)
(host.PRIVATE / 'reboot-runtime-r2-host-private.log').write_bytes(result.stdout + result.stderr)
print(result.stdout.decode().strip())
