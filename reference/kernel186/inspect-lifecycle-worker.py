"""Observe the exact worker handle, never infer liveness from pending markers."""
from pathlib import Path
import json
import host

pid = int((host.PRIVATE / 'lifecycle-worker-pid-private.txt').read_text())
code = '''from pathlib import Path
import json
import subprocess
assert Path('/proc/sys/kernel/random/boot_id').read_bytes() == Path('/var/lib/samurai/k186-baseline/boot-id-private.txt').read_bytes()
pid = %d
p = Path('/proc') / str(pid)
cmd = (p / 'cmdline').read_bytes() if p.exists() else b''
live = b'/var/lib/samurai/k186-tools/test-slpi-lifecycle.sh' in cmd
root = Path('/var/lib/samurai/k186-slpi-lifecycle')
report = {'worker_handle_live': live, 'worker_proc_present': p.exists(), 'files': sorted(x.name for x in root.iterdir()) if root.exists() else [],
    'slpi': Path('/sys/class/remoteproc/remoteproc0/state').read_text().strip(),
    'sensor_power': Path('/sys/devices/platform/sensor-power/state').read_text().strip()}
for name in ['trial-exit.txt','start-exit.txt','census-exit.txt','stop1-exit.txt','start2-exit.txt']:
    path = root / name
    if path.exists(): report[name] = path.read_text().strip()
text = Path('/var/lib/samurai/k186-lifecycle-worker-private.log').read_text(errors='replace')
Path('/var/lib/samurai/k186-baseline/worker-inspection-private.json').write_text(json.dumps(report,indent=2)+'\\n')
print(json.dumps(report))
print(text[-1500:])
''' % pid
p = host.ssh('python3 -', input=code.encode())
(host.PRIVATE / 'lifecycle-worker-inspection-private.log').write_bytes(p.stdout + p.stderr)
print(p.stdout.decode().strip())
