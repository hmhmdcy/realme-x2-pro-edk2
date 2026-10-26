from pathlib import Path
import hashlib
import json
import os
import subprocess

os.umask(0o077)
out = Path('/var/lib/samurai/k188-persistent-client')
assert not out.exists()
assert os.uname().version.startswith('#183 ')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes() == Path('/var/lib/samurai/k188-reboot-runtime/boot-id-private.txt').read_bytes()
out.mkdir(mode=0o700)
before = subprocess.check_output(['dmesg']).decode()
(out / 'dmesg-before-private.txt').write_text(before)
state = Path('/run/samurai-ssc/state.json').read_bytes()
source = '/var/lib/samurai/k188-deploy/source-manifest-private.sha256'
database = Path('/lib/apk/db/installed').read_bytes()
system_lib = Path('/usr/lib/libssc.so.2').read_bytes()
report = {}
subprocess.run(['samurai-ssc', 'status'], check=True, stdout=subprocess.DEVNULL)
p = subprocess.run(['su', '-s', '/bin/sh', 'cy122', '-c', 'python3 /var/lib/samurai/k188-tools/test-persistent-client.py'],
                   capture_output=True, timeout=25)
(out / 'desktop-client-private.txt').write_bytes(p.stdout + p.stderr)
assert p.returncode == 0
report.update(json.loads(p.stdout))
for sensor, label in [('gyroscope', 'Gyroscope'), ('magnetometer', 'Magnetometer'), ('compass', 'Compass')]:
    p = subprocess.run(['ssccli', '--debug', '--sensor', sensor, '--timeout', '3'],
                       capture_output=True, timeout=20)
    raw = (p.stdout + p.stderr).decode(errors='replace')
    (out / (sensor + '-private.log')).write_bytes(p.stdout + p.stderr)
    record = dict(exit=p.returncode, samples=raw.count(label + ' sensor measurement:'),
                  disabled=(label + ' sensor disabled').lower() in raw.lower())
    assert record['exit'] == 0 and record['samples'] > 0 and record['disabled']
    report[sensor] = record
assert Path('/run/samurai-ssc/state.json').read_bytes() == state
assert Path('/lib/apk/db/installed').read_bytes() == database
assert Path('/usr/lib/libssc.so.2').read_bytes() == system_lib
subprocess.run(['sha256sum', '-c', source], check=True, stdout=subprocess.DEVNULL)
subprocess.run(['samurai-ssc', 'status'], check=True, stdout=subprocess.DEVNULL)
after = subprocess.check_output(['dmesg']).decode()
(out / 'dmesg-after-private.txt').write_text(after)
assert after.startswith(before)
extra = after[len(before):]
faults = {key: extra.count(value) for key, value in dict(warning='WARNING:', oops='Oops:',
    scm='Assign memory protection call failed', fastrpc='probe with driver qcom,fastrpc failed',
    slpi_start='2400000.remoteproc: start timed out', slpi_stop='2400000.remoteproc: timed out on wait',
    asoc='ASoC error', gpu='gpu fault:', bluetooth='Frame reassembly failed').items()}
assert not any(faults.values())
report.update(stage=188, persistent_service_remained_running=True, daemon_identity_preserved=True,
    source_archive_unchanged=True, default_system_library_unchanged=True,
    package_database_unchanged=True, fault_delta=faults,
    human_motion_and_absolute_accuracy_verified=False,
    uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]))
(out / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
