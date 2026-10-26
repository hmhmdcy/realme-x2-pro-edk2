import host, json
code = r'''
from pathlib import Path
import json
root=Path('/var/lib/samurai');boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot!=(root/'k207-before-reboot/boot-id-private.txt').read_bytes()
watch_path=root/'gnss-assist/watch-state.json';watch=json.loads(watch_path.read_text()) if watch_path.exists() else {}
cache=Path('/run/samurai-wifi/tftp-rw/mcfg.tmp')
report=dict(fresh_different_boot_verified=True,current_runtime_guard_present=(root/'k207-runtime/boot-id-private.txt').exists(),uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]),watch_running=watch.get('running'),time_prepared=watch.get('time_prepared'),time_preparation_starts=watch.get('time_preparation_starts'),time_preparation_completions=watch.get('time_preparation_completions'),worker_starts=watch.get('worker_starts'),worker_completions=watch.get('worker_completions'),mcfg_cache_present=cache.is_file(),mcfg_cache_bytes=cache.stat().st_size if cache.is_file() else None,remoteprocs={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')})
print(json.dumps(report))
'''
p = host.ssh('python3 -', input=code.encode(), timeout=25)
(host.PRIVATE / 'pending-newboot-private.json').write_bytes(p.stdout)
print(p.stdout.decode())
