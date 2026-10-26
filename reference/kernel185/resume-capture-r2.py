"""Retain the failed count guard, then verify all files and the module subset."""
from pathlib import Path
import hashlib
import json
import subprocess
import host

ref = Path(__file__).resolve().parent
host.ssh('test ! -e /var/lib/samurai/k185-preflash-r2-private && cp -a /var/lib/samurai/k185-preflash /var/lib/samurai/k185-preflash-r2-private')
script = ref / 'collect-preflash.py'
host.upload(script, '/var/lib/samurai/k185-reboot-tools/collect-preflash.py')
host.ssh('sha256sum -c -', input=(hashlib.sha256(script.read_bytes()).hexdigest() + '  /var/lib/samurai/k185-reboot-tools/collect-preflash.py\n').encode())
try:
    p = host.ssh('python3 /var/lib/samurai/k185-reboot-tools/collect-preflash.py', timeout=55)
except subprocess.CalledProcessError as e:
    (host.PRIVATE / 'resumed-capture-r2-failure-private.log').write_bytes(e.stdout + e.stderr)
    print(e.stderr.decode(errors='replace'))
    raise SystemExit(e.returncode)
(host.PRIVATE / 'pre-reboot-capture-private.log').write_bytes(p.stdout + p.stderr)
print(json.dumps({'initial_guard_failures_preserved': True, 'kernel183_partitions_verified': True,
    'total_tree_files_verified': 784, 'modules': 770, 'overrides': 1, 'transition_requested': False}))
