from pathlib import Path
import host

data=(Path(__file__).resolve().parent.parent/'kernel185/collect-reboot-runtime.py').read_text()
data=data.replace('k185-reboot-runtime','k189-reboot-runtime').replace('k185-preflash','k189-preflash').replace("'stage': 185","'stage': 189")
p=host.ssh('python3 -',input=data.encode(),timeout=120)
(host.PRIVATE/'reboot-runtime-host-private.log').write_bytes(p.stdout+p.stderr)
print(p.stdout.decode().strip())
