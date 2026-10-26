"""Verify the already requested transition; never resend RESTART2."""
from pathlib import Path
import os
import subprocess
import sys
import host

assert (host.PRIVATE / 'r2-reboot-request-private.json').exists()
assert not (host.PRIVATE / 'r2-fastboot-reboot-private.json').exists()
ref = Path(__file__).resolve().parent
text = (ref / 'fastboot-reboot-current.py').read_text().replace('k184', 'k184r2')
text = text.replace("host.PRIVATE / '", "host.PRIVATE / 'r2-")
dest = host.PRIVATE / 'reboot-r2-tools-private/fastboot-reboot-wait.py'
assert not dest.exists()
dest.write_text(text)
subprocess.run([sys.executable, str(dest)], env=dict(os.environ, PYTHONPATH=str(ref)), check=True)
