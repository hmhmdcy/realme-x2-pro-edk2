"""Validate sealed new-boot traces without exposing device identifiers."""
from pathlib import Path
import collections
import hashlib
import json
import re
import statistics
import tarfile

root = Path('/mnt/e/RealmeX2Pro edk2')
ref = root / 'reference/kernel141'
out = Path('/mnt/e/edk2-samurai-out/kernel141')
archive_path = out / 'reboot140-startup-private.tar.gz'
with tarfile.open(archive_path) as archive:
    data = {}
    for member in archive:
        assert not member.issym() and not member.islnk()
        if member.isfile():
            name = member.name.removeprefix('./')
            assert not Path(name).is_absolute() and '..' not in Path(name).parts and name not in data
            data[name] = archive.extractfile(member).read()
for line in data['SHA256SUMS'].decode().splitlines():
    digest, name = line.split('  ', 1)
    assert hashlib.sha256(data[name.removeprefix('./')]).hexdigest() == digest
assert data['boot-id-private.txt'] != (out / 'source-boot-id-private.txt').read_bytes()
report = json.loads(data['startup-result.json'])
assert report['same_new_boot'] and report['new_boot'] and report['error'] is None
assert report['current_kernel'] == 140 and report['trace_instance_removed']
assert report['no_output_or_application_workload_requested']
samples = json.loads(data['startup-samples-private.json'])
assert len(samples) == report['sample_count'] and samples
stats = json.loads(data['trace-stats-private.json'])
loss = {cpu: {name: int(re.search(r'^' + name + r': (\d+)$', value, re.M).group(1))
              for name in ['overrun', 'commit overrun', 'dropped events']}
        for cpu, value in stats.items()}
assert len(stats) == 8
loss_free = not any(number for cpu in loss.values() for number in cpu.values())

def parse(text):
    result = []
    for line in text.splitlines():
        match = re.search(r'\s(\d+\.\d+):\s+([a-zA-Z0-9_]+):\s*(.*)$', line)
        if match:
            result.append(dict(seconds=float(match.group(1)), name=match.group(2), body=match.group(3)))
    return result

events = parse(data['startup-trace-private.txt'].decode())
default_events = parse(data['default-display-final-private.txt'].decode())
timeouts = [event for event in events if event['name'] == 'dpu_enc_frame_done_timeout']
default_timeouts = [event for event in default_events if event['name'] == 'dpu_enc_frame_done_timeout']
dmesg_timeouts = []
for line in data['dmesg-final-private.txt'].decode().splitlines():
    match = re.match(r'\[\s*(\d+\.\d+)\].*frame done timeout', line)
    if match:
        dmesg_timeouts.append(float(match.group(1)))
calibration = None
if len(default_timeouts) == len(dmesg_timeouts) and dmesg_timeouts:
    deltas = [timestamp - event['seconds'] for timestamp, event in zip(dmesg_timeouts, default_timeouts)]
    calibration = dict(paired_timeout_events=len(deltas),
        observed_median_dmesg_minus_mono_seconds=round(statistics.median(deltas), 6),
        observed_pair_spread_microseconds=round((max(deltas) - min(deltas)) * 1e6, 3),
        this_new_boot_only=True, full_clock_identity_proven=False)
windows = []
for event in timeouts:
    stamp = event['seconds']
    selected = [item for item in events if stamp - 0.16 <= item['seconds'] <= stamp + 0.09]
    windows.append(dict(timeout_trace_seconds=stamp,
        event_order=[dict(relative_ms=round((item['seconds'] - stamp) * 1000, 3),
                          name=item['name'], body=item['body']) for item in selected]))
event_counts = collections.Counter(event['name'] for event in events)
report.update(archive_sha256=hashlib.sha256(archive_path.read_bytes()).hexdigest(),
    archive_manifest_verified=True, new_boot_distinct_from_preflight=True,
    trace_clock='mono', trace_loss=loss, trace_loss_free=loss_free,
    own_trace_timeout_events=len(timeouts), retained_default_trace_timeout_events=len(default_timeouts),
    final_dmesg_timeout_events=len(dmesg_timeouts), events=dict(event_counts),
    first_sample_uptime_seconds=samples[0]['uptime_seconds'],
    last_sample_uptime_seconds=samples[-1]['uptime_seconds'],
    desktop_stable_final=report['phosh_present_final'] and report['phoc_present_final'],
    pp_trace_new_count_is_atomic_operation_boolean=True,
    new_boot_clock_calibration=calibration, startup_fix_proven=False,
    gpu_and_charging_acceptance_pending=True, goal_complete=False)
(ref / 'reboot140-startup-validation.json').write_text(json.dumps(report, indent=2) + '\n')
(out / 'parsed-startup-events-private.json').write_text(json.dumps(events, indent=2) + '\n')
(out / 'startup-timeout-windows-private.json').write_text(json.dumps(windows, indent=2) + '\n')
print(json.dumps(report, indent=2))
for index, window in enumerate(windows, 1):
    selected = [item for item in window['event_order'] if item['name'].startswith('dpu_enc_')
                or item['name'].startswith('msm_atomic_') or item['name'] in ['dpu_hw_ctl_trigger_start']]
    for item in selected:
        item['body'] = re.sub(r'\b(?:0x)?[0-9a-f]{8,16}\b', '[redacted]', item['body'])
    print('TIMEOUT_WINDOW', index, json.dumps(selected, indent=2))
