import json
import host

native = r'''
from pathlib import Path
import json
root=Path('/var/lib/samurai')
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot==(root/'k207r2-runtime/boot-id-private.txt').read_bytes()
watch=json.loads((root/'gnss-assist/watch-state.json').read_text())
print(json.dumps(dict(uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]), watch_running=watch.get('running'),time_prepared=watch.get('time_prepared'),time_preparation_starts=watch.get('time_preparation_starts'),time_preparation_completions=watch.get('time_preparation_completions'),worker_starts=watch.get('worker_starts'),worker_completions=watch.get('worker_completions'))))
'''
p = host.ssh('python3 -', input=native.encode(), timeout=25)
(host.PRIVATE / 'readiness-observation-private.json').write_bytes(p.stdout)
print(p.stdout.decode())
