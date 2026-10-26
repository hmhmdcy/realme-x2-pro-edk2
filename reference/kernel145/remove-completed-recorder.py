"""Remove only the validated, completed temporary boot recorder."""
from pathlib import Path
import hashlib
import json
import os
import subprocess

base = Path('/var/lib/samurai/k145-pre-reboot')
startup = Path('/var/lib/samurai/k145-first145-startup')
out = Path('/var/lib/samurai/k145-recorder-cleanup')
metadata = json.loads(Path('/tmp/k145-startup-irq-idle-validation.json').read_text())
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert os.geteuid() == 0 and os.uname().version.startswith('#145 ')
assert boot == startup.joinpath('boot-id-private.txt').read_bytes()
assert boot != Path('/var/lib/samurai/k145-preflash/boot-id-private.txt').read_bytes()
assert metadata['archive_manifest_verified'] and metadata['trace_instance_removed']
assert metadata['error'] is None and metadata['trace_stream_reader_errors'] == []
assert hashlib.sha256(Path('/tmp/k145-first145-startup-private.tar.gz').read_bytes()).hexdigest() == metadata['archive_sha256']
assert startup.joinpath('complete-private.txt').read_text().strip() == 'K145_RECORDER_COMPLETE'
assert not Path('/sys/kernel/tracing/instances/k145-startup').exists()
assert not out.exists()
pidfile = Path('/run/k145-startup-trace.pid')
if pidfile.exists():
    pid = int(pidfile.read_text().strip())
    assert not Path('/proc').joinpath(str(pid)).exists(), 'Recorded process still exists; do not stop it'
for line in base.joinpath('temporary-recorder.sha256').read_text().splitlines():
    digest, name = line.split('  ', 1)
    assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest
service = Path('/etc/init.d/k145-startup-trace')
link = Path('/etc/runlevels/boot/k145-startup-trace')
assert link.is_symlink() and os.readlink(link) == str(service)
out.mkdir(mode=0o700)
out.joinpath('boot-id-private.txt').write_bytes(boot)
with out.joinpath('stop-private.txt').open('w') as file:
    subprocess.run(['rc-service', 'k145-startup-trace', 'stop'], stdout=file, stderr=subprocess.STDOUT, check=True)
with out.joinpath('runlevel-remove-private.txt').open('w') as file:
    subprocess.run(['rc-update', 'del', 'k145-startup-trace', 'boot'], stdout=file, stderr=subprocess.STDOUT, check=True)
assert not link.exists() and not link.is_symlink() and not pidfile.exists()
service.unlink()
with out.joinpath('gui-check.txt').open('w') as file:
    subprocess.run(['sha256sum', '-c', '/var/lib/samurai/k135-preflash/gui-config.sha256'], stdout=file, stderr=subprocess.STDOUT, check=True)
assert boot == Path('/proc/sys/kernel/random/boot_id').read_bytes()
report = dict(stage=145, kernel_build=145, same_startup_boot=True,
    sealed_archive_sha256_matches_host=True, recorder_already_terminal=True,
    recorder_service_removed=not service.exists(), boot_link_removed=not link.is_symlink(),
    recorder_pidfile_removed=not pidfile.exists(), own_trace_instance_absent=True,
    gui_three_files_preserved=True, process_killed=False,
    taint=int(Path('/proc/sys/kernel/tainted').read_text()), goal_complete=False)
out.joinpath('cleanup-validation.json').write_text(json.dumps(report, indent=2) + '\n')
out.joinpath('SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest() + '  ./' + p.name + '\n'
    for p in sorted(out.iterdir()) if p.is_file()))
subprocess.run(['tar', '-C', str(out), '-czf', '/tmp/k145-recorder-cleanup-private.tar.gz', '.'], check=True, timeout=20)
print(json.dumps(report, indent=2))
