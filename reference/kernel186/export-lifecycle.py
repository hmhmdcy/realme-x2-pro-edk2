"""Capture completed worker evidence before further SLPI experiments."""
from pathlib import Path
import hashlib
import json
import re
import tarfile
import host

p = host.ssh('test -f /var/lib/samurai/k186-slpi-lifecycle/trial-exit.txt && sha256sum /tmp/k186-slpi-lifecycle.tar')
digest = p.stdout.decode().split()[0]
dest = host.PRIVATE / 'k186-slpi-lifecycle-private.tar'
host.download('/tmp/k186-slpi-lifecycle.tar', dest)
assert hashlib.sha256(dest.read_bytes()).hexdigest() == digest
folder = host.PRIVATE / 'slpi-lifecycle-evidence-private'
with tarfile.open(dest) as tar:
    tar.extractall(folder, filter='data')
def text(name):
    return (folder / name).read_text()
assert text('trial-exit.txt').strip() == '0'
assert text('start-exit.txt').strip() == text('stop1-exit.txt').strip() == text('start2-exit.txt').strip() == '0'
assert text('state-after-stop1.txt').strip() == 'offline' and text('state-after-start2.txt').strip() == 'running'
assert text('slpi-final-state.txt').strip() == 'offline' and text('power-final.txt').strip() == 'vdd=0 vddio=0'
assert text('source-before.txt') == text('source-after.txt') and text('nv-before.txt') == text('nv-after.txt')
before = text('dmesg-before.txt')
after = text('dmesg-final.txt')
phase_logs = [text(name) for name in ['first-running-dmesg-private.txt', 'after-stop1-dmesg-private.txt', 'after-start2-dmesg-private.txt']]
assert all(value.startswith(before) for value in phase_logs)
covered_delta = phase_logs[-1][len(before):]
faults = {key: covered_delta.count(value) for key, value in {
    'warning': 'WARNING:', 'oops': 'Oops:', 'slpi_start_timeout': '2400000.remoteproc: start timed out',
    'slpi_stop_ack_timeout': '2400000.remoteproc: timed out on wait', 'slpi_shutdown_failure': '2400000.remoteproc: failed to shutdown',
    'asoc': 'ASoC error', 'bluetooth_reassembly': 'Frame reassembly failed', 'gpu': 'gpu fault:', 'dpu': 'Frame done timeout'}.items()}
attributes = json.loads((folder / 'attributes/summary.json').read_text())
report = dict(stage=186, kernel_build=183, trial_exit=0, first_start_exit=0,
    dsp_first_stop_exit=0, restart_exit=0, restart_state='running',
    normal_file_service_alive_until_first_dsp_stop=True, power_off_gap_seconds=5,
    first_census_exit=int(text('census-exit.txt').strip()),
    stopped_and_power_off_after_trial=True, fault_delta_through_second_start=faults,
    source_and_nv_unchanged=True, evidence_archive_sha256=digest,
    original_firmware_used=True, no_reboot_or_flash=True,
    restart_file_service_and_measurements_verified=False,
    causal_stop_order_fix_proven=False, more_complete_restart_trial_pending=True,
    complete_restart_chain_passed=False, final_log_ring_wrapped=not after.startswith(before),
    full_trial_log_window_continuously_covered=False,
    observed_final_scm_assignment_failures_lower_bound=after.count('Assign memory protection call failed -22'),
    observed_final_fastrpc_probe_failures_lower_bound=after.count('probe with driver qcom,fastrpc failed with error -22'),
    remaining_failure='FastRPC reserved-pool ownership is not reclaimed; subsequent probe repeatedly fails -22')
ref = Path(__file__).resolve().parent
(ref / 'lifecycle-validation.json').write_text(json.dumps(report, indent=2) + '\n')
(host.PRIVATE / 'first-census-summary-private.json').write_text(json.dumps(attributes, indent=2) + '\n')
print(json.dumps(report))
print(json.dumps({'first_census_complete': attributes['complete'],
    'sensor_data_types': sorted({value for item in attributes['inventory'] for value in item.get('data_type', []) if isinstance(value, str)}),
    'accel_seen': bool(attributes['suid_types'].get('accel')), 'gyro_seen': bool(attributes['suid_types'].get('gyro'))}))
