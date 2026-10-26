"""Seal a recorder that never started, then remove its exact temporary service.

This is a one-shot closeout, not a retry or a successful startup trace.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import subprocess

base = Path('/var/lib/samurai/k145-pre-reboot')
startup = Path('/var/lib/samurai/k145-first145-startup')
out = Path('/var/lib/samurai/k145-inactive-recorder-closeout')
service = Path('/etc/init.d/k145-startup-trace')
link = Path('/etc/runlevels/boot/k145-startup-trace')
pidfile = Path('/run/k145-startup-trace.pid')
trace = Path('/sys/kernel/tracing/instances/k145-startup')
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert os.geteuid() == 0 and os.uname().version.startswith('#145 ')
assert boot == Path('/tmp/k145-closeout-expected-boot-id-private.txt').read_bytes()
assert boot == Path('/var/lib/samurai/k145-first-runtime/boot-id-private.txt').read_bytes()
assert boot != Path('/var/lib/samurai/k145-preflash/boot-id-private.txt').read_bytes()
assert not out.exists() and not startup.exists() and not trace.exists()
assert not pidfile.exists()
for path in Path('/proc').glob('[0-9]*/cmdline'):
    try:
        cmdline = path.read_bytes()
    except (FileNotFoundError, ProcessLookupError, PermissionError):
        continue
    assert str(base / 'capture-next-startup.py').encode() not in cmdline
assert not base.joinpath('recorder-private.log').exists()
assert not base.joinpath('recorder-error-private.log').exists()
assert not Path('/tmp/k145-first145-startup-private.tar.gz').exists()
expected = {}
for line in base.joinpath('temporary-recorder.sha256').read_text().splitlines():
    digest, name = line.split('  ', 1)
    expected[name] = digest
    assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest
assert len(expected) == 3 and str(service) in expected
assert link.is_symlink() and os.readlink(link) == str(service)
status = subprocess.run(['rc-service', 'k145-startup-trace', 'status'],
                        capture_output=True, text=True, timeout=10)
assert 'status: stopped' in status.stdout + status.stderr

def counts():
    raw = subprocess.check_output(['dmesg'])
    text = raw.decode(errors='replace')
    return raw, {name: len(re.findall(pattern, text)) for name, pattern in [
        ('gpu_faults', r'gpu fault:'), ('dpu_timeouts', r'frame done timeout'),
        ('dsi_errors', r'dsi_err_worker'), ('kernel_warns', r'WARNING:'),
        ('dma_tx_prepare_failure', r'unable to prepare channel')]}

out.mkdir(mode=0o700)
evidence = out / 'evidence-private'
evidence.mkdir(mode=0o700)
evidence.joinpath('boot-id-private.txt').write_bytes(boot)
evidence.joinpath('service-status-private.txt').write_text(status.stdout + status.stderr)
for name in expected:
    shutil.copyfile(name, evidence / Path(name).name)
shutil.copyfile(base / 'temporary-recorder.sha256', evidence / 'installed-files-private.sha256')
for name in ['gui-config-before-service-check.txt', 'service-install-private.txt']:
    if (base / name).is_file():
        shutil.copyfile(base / name, evidence / name)
for name, source in [('openrc-deptree-private.txt', '/run/openrc/deptree'),
                     ('openrc-softlevel-private.txt', '/run/openrc/softlevel'),
                     ('init-cmdline-private.bin', '/proc/1/cmdline'),
                     ('rc-log-private.txt', '/var/log/rc.log')]:
    path = Path(source)
    if path.is_file() and path.stat().st_size < 10 * 1024 * 1024:
        evidence.joinpath(name).write_bytes(path.read_bytes())
for level in ['boot', 'default']:
    result = subprocess.run(['rc-status', level], capture_output=True, timeout=10)
    evidence.joinpath('runlevel-' + level + '-private.txt').write_bytes(result.stdout + result.stderr)
before_raw, before_counts = counts()
evidence.joinpath('dmesg-before-private.txt').write_bytes(before_raw)
failure = dict(stage=145, kernel_build=145, startup_capture_success=False,
    service_installed_exact=True, service_status_stopped=True,
    recorder_process_absent=True, pidfile_absent=True, trace_instance_absent=True,
    startup_directory_absent=True, recorder_logs_absent=True,
    archive_absent=True, failure_cause_confirmed=False,
    hardware_repair_accepted=False, goal_complete=False)
evidence.joinpath('recorder-failure-validation.json').write_text(json.dumps(failure, indent=2) + '\n')
evidence.joinpath('SHA256SUMS').write_text(''.join(
    hashlib.sha256(p.read_bytes()).hexdigest() + '  ./' + p.name + '\n'
    for p in sorted(evidence.iterdir()) if p.is_file()))
sealed = out / 'failure-before-cleanup-private.tar.gz'
subprocess.run(['tar', '-C', str(evidence), '-czf', str(sealed), '.'], check=True, timeout=20)
sealed_hash = hashlib.sha256(sealed.read_bytes()).hexdigest()

# The service was never running: do not call its completion-only stop action.
with out.joinpath('runlevel-remove-private.txt').open('w') as file:
    subprocess.run(['rc-update', 'del', 'k145-startup-trace', 'boot'],
                   stdout=file, stderr=subprocess.STDOUT, check=True, timeout=10)
assert not link.exists() and not link.is_symlink()
assert hashlib.sha256(service.read_bytes()).hexdigest() == expected[str(service)]
service.unlink()
with out.joinpath('gui-check-private.txt').open('w') as file:
    subprocess.run(['sha256sum', '-c', '/var/lib/samurai/k135-preflash/gui-config.sha256'],
                   stdout=file, stderr=subprocess.STDOUT, check=True, timeout=10)
after_raw, after_counts = counts()
out.joinpath('dmesg-after-private.txt').write_bytes(after_raw)
assert boot == Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert not trace.exists() and not pidfile.exists() and not service.exists()
report = dict(stage=145, kernel_build=145, same_verified_runtime_boot=True,
    inactive_recorder_failure_sealed=True, failure_archive_sha256=sealed_hash,
    recorder_never_started=True, startup_capture_success=False,
    startup_trace_unavailable=True, failure_cause_confirmed=False,
    boot_link_removed=True, exact_service_removed=True,
    own_trace_instance_absent=True, pidfile_absent=True, process_killed=False,
    recorder_source_and_evidence_preserved=True, gui_three_files_preserved=True,
    counts_before=before_counts, counts_after=after_counts,
    no_new_counted_faults=before_counts == after_counts,
    taint=int(Path('/proc/sys/kernel/tainted').read_text()),
    gpu_probe_allowed=False, hardware_repair_accepted=False, goal_complete=False)
out.joinpath('cleanup-validation.json').write_text(json.dumps(report, indent=2) + '\n')
out.joinpath('SHA256SUMS').write_text(''.join(
    hashlib.sha256(p.read_bytes()).hexdigest() + '  ./' + str(p.relative_to(out)) + '\n'
    for p in sorted(out.rglob('*')) if p.is_file() and p != out / 'SHA256SUMS'))
subprocess.run(['tar', '-C', str(out), '-czf', '/tmp/k145-inactive-recorder-closeout-private.tar.gz', '.'],
               check=True, timeout=20)
print(json.dumps(report, indent=2))
