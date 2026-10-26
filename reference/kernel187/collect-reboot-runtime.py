from pathlib import Path
import host

source=(Path(__file__).resolve().parent.parent/'kernel185/collect-reboot-runtime.py').read_text()
source=source.replace('/var/lib/samurai/k185-reboot-runtime','/var/lib/samurai/k187-reboot-runtime')
source=source.replace('/var/lib/samurai/k185-preflash','/var/lib/samurai/k187-preflash')
source=source.replace("'stage': 185","'stage': 187")
p=host.ssh('python3 -',input=source.encode(),timeout=55)
(host.PRIVATE/'reboot-runtime-host-private.log').write_bytes(p.stdout+p.stderr)
print(p.stdout.decode().strip())
