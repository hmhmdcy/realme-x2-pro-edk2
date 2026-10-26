"""Preserve the pre-daemon partial capture, then observe normal startup readiness."""
from pathlib import Path
import subprocess
import host

host.ssh('test ! -e /var/lib/samurai/k185-reboot-runtime-initial-private && cp -a /var/lib/samurai/k185-reboot-runtime /var/lib/samurai/k185-reboot-runtime-initial-private')
script = Path(__file__).resolve().parent / 'collect-reboot-runtime.py'
try:
    p = host.ssh('python3 -', input=script.read_bytes(), timeout=55)
except subprocess.CalledProcessError as e:
    (host.PRIVATE / 'reboot-runtime-resumed-failure-private.log').write_bytes(e.stdout + e.stderr)
    print(e.stderr.decode(errors='replace'))
    raise SystemExit(e.returncode)
(host.PRIVATE / 'reboot-runtime-resumed-host-private.log').write_bytes(p.stdout + p.stderr)
print(p.stdout.decode().strip())
