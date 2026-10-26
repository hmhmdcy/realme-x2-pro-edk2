from pathlib import Path
import hashlib
import json
import subprocess
import tarfile
import host

result = host.ssh('test -f /var/lib/samurai/k184-sensor-light-v1/trial-exit.txt && tar -C /var/lib/samurai -czf /tmp/k184-light-evidence-private.tar.gz k184-baseline k184-baseline-r2 k184-sensor-light-v1 && sha256sum /tmp/k184-light-evidence-private.tar.gz')
expected = result.stdout.decode().split()[0]
local = host.PRIVATE / 'k184-light-evidence-private.tar.gz'
host.download('/tmp/k184-light-evidence-private.tar.gz', local)
assert hashlib.sha256(local.read_bytes()).hexdigest() == expected
with tarfile.open(local) as tar:
    tar.extractall(host.PRIVATE / 'light-evidence-private', filter='data')
root = host.PRIVATE / 'light-evidence-private/k184-sensor-light-v1'
report = json.loads((root / 'validation.json').read_text())
assert (root / 'trial-exit.txt').read_text().strip() == '0'
assert (root / 'source-before.txt').read_bytes() == (root / 'source-after.txt').read_bytes()
assert (root / 'nv-before.txt').read_bytes() == (root / 'nv-after.txt').read_bytes()
assert report['taint'] == 0 and report['slpi_final'] == 'offline'
assert report['sensor_power_final'] == 'vdd=0 vddio=0' and report['recovery_final'] == 'enabled'
report.update(kernel_build=183, archive_sha256=expected, original_sources_verified=True,
              radio_nv_verified=True, firmware_replaced=False,
              claim='SSC light transport and sensor-name mismatch confirmed; physical lux accuracy remains unvalidated')
ref = Path(__file__).resolve().parent
(ref / 'light-runtime-validation.json').write_text(json.dumps(report, indent=2) + '\n')
baseline = json.loads((host.PRIVATE / 'light-evidence-private/k184-baseline-r2/summary.json').read_text())
(ref / 'baseline-validation.json').write_text(json.dumps(baseline, indent=2) + '\n')
print(json.dumps({'archive_sha_verified': True, 'samples': report['samples'],
                  'light_transport_passed': True, 'physical_lux_accuracy_proven': False,
                  'original_sources_and_nv_verified': True, 'slpi_stopped_and_power_released': True}))
