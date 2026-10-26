"""One explicitly handed-over, bounded read-only device observation.

Does not upload/install files or mutate device state. On analyzer failure, use
the retained stdout for re-audit rather than repeating device sampling.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import shlex

ref = Path(__file__).resolve().parent
out = Path('/mnt/e/edk2-samurai-out/charging-management-20261023/health-continued')
out.mkdir(parents=True, exist_ok=True, mode=0o700)
raw = out / 'observation-r1-private.json'
assert not raw.exists(), 'Use the retained observation; do not silently repeat'
source = (ref / 'charging-health.py').read_text()
digest = hashlib.sha256(source.encode()).hexdigest()
source_snapshot = out / 'charging-health-r1.py'
assert not source_snapshot.exists(), 'Do not replace the source of an existing observation'
source_snapshot.write_text(source)
test = json.loads((ref / 'health-observer-test-result.json').read_text())
assert test['passed'] and test['tested_files']['charging-health.py'] == digest
spec = importlib.util.spec_from_file_location('charging_window', ref / 'device-window.py')
window = importlib.util.module_from_spec(spec)
spec.loader.exec_module(window)
guard = "from pathlib import Path\nassert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k449-adopted/boot-id-private.txt').read_bytes()\n"
response = window.host.ssh('python3 -c ' + shlex.quote(guard + source), timeout=180)
raw.write_bytes(response.stdout)
(out / 'observation-r1-stderr-private.txt').write_bytes(response.stderr)
response.check_returncode()
data = json.loads(response.stdout)
assert data['manifest_sha256'] == '34d46f4cf449f0c7a50590e0de3c07d84762c19ef1dd1a22e20f6cf66a24d5a7'
spec = importlib.util.spec_from_file_location('charging_health', ref / 'charging-health.py')
health = importlib.util.module_from_spec(spec)
spec.loader.exec_module(health)
report = health.audit(data)
report['observer_sha256'] = digest
report['private_capture_sha256'] = hashlib.sha256(response.stdout).hexdigest()
report['samples_are_cached_kernel_telemetry'] = True
report['configuration_or_service_writes'] = 0
report['range'] = {name: [min(row['telemetry'][name] for row in data['samples']),
                        max(row['telemetry'][name] for row in data['samples'])]
                   for name in ['temp_decic', 'cell1_uv', 'cell2_uv', 'pack_uv', 'age_ms', 'session_seconds']}
report['charger_status_counts'] = {str(value): sum(row['charger_status'] == value for row in data['samples'])
                                  for value in set(str(row['charger_status']) for row in data['samples'])}
(ref / 'health-observation-result.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
assert report['passed'], 'Retain raw evidence and investigate; no automatic retry or control action'
