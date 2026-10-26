from pathlib import Path
import collections
import hashlib
import json
import re
import tarfile

r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel141'
out = Path('/mnt/e/edk2-samurai-out/kernel141')
with tarfile.open(out / 'normal-wake-private.tar.gz') as archive:
    data = {m.name.removeprefix('./'): archive.extractfile(m).read() for m in archive if m.isfile()}
for line in data['SHA256SUMS'].decode().splitlines():
    digest, name = line.split('  ', 1)
    assert hashlib.sha256(data[name.removeprefix('./')]).hexdigest() == digest
assert data['boot-id-private.txt'] == (out.parent / 'kernel140/embedded-boot-id-private.txt').read_bytes()
report = json.loads(data['wake-result.json'])
assert report['error'] is None and report['same_boot'] and report['taint'] == 0 and report['pids_unchanged']
assert report['output_enabled_after_request'] and report['counts_before'] == report['counts_after']
for name, count in [('package-check.txt', 2), ('nv-check.txt', 6), ('source-check.txt', 4), ('vendor-check.txt', 1)]:
    assert data[name].count(b': OK') == count and b'FAILED' not in data[name]
trace = data['wake-trace-private.txt'].decode()
stats = json.loads(data['trace-stats-private.json'])
assert all(re.search(r'^overrun: 0$', text, re.M) and re.search(r'^commit overrun: 0$', text, re.M) and re.search(r'^dropped events: 0$', text, re.M) for text in stats.values())
events = []
for line in trace.splitlines():
    m = re.search(r'\s(\d+\.\d+):\s+([a-zA-Z0-9_]+):\s*(.*)$', line)
    if m:
        events.append(dict(seconds=float(m.group(1)), name=m.group(2), body=m.group(3)))
counts = collections.Counter(e['name'] for e in events)
last_arm = None
latencies = []
arms = 0
idle_arms = 0
for event in events:
    if event['name'] != 'dpu_enc_frame_watchdog':
        continue
    if 'action=arm ' in event['body']:
        last_arm = event['seconds']; arms += 1
    elif 'action=arm_idle ' in event['body']:
        idle_arms += 1
    elif 'action=complete ' in event['body'] and last_arm is not None:
        latencies.append(round((event['seconds'] - last_arm) * 1000, 3)); last_arm = None
samples = json.loads(data['samples-private.json'])
delayed = json.loads(data['delayed-private.json'])
assert all(s['same_boot'] and s['taint'] == 0 and s['counts'] == report['counts_before'] for s in delayed)
report.update(archive_sha256_verified=True, trace_loss_free=True, events=dict(counts),
    hardware_pp_done_interrupts=counts['dpu_enc_phys_cmd_pp_tx_done'],
    hardware_rdptr_vblank_callbacks=counts['dpu_crtc_vblank_cb'],
    watchdog_arms=arms, watchdog_idle_arms=idle_arms,
    matched_watchdog_completion_latencies_ms=latencies,
    max_matched_completion_ms=max(latencies) if latencies else None,
    crtc_active_all_samples=all(s['active'] for s in samples),
    backlight_positive_all_samples=all(any(int(bl.get('brightness', '0')) > 0 and bl.get('bl_power') == '0' for bl in s['backlights'].values()) for s in samples),
    delayed_samples=8, source_and_packages_preserved=True,
    real_pp_and_vblank_completion_observed=counts['dpu_enc_phys_cmd_pp_tx_done'] > 0 and counts['dpu_crtc_vblank_cb'] > 0,
    standalone_gpu_failure_not_retested=True, startup_timeouts_not_fixed=True,
    pp_trace_new_count_is_atomic_operation_boolean=True)
assert report['real_pp_and_vblank_completion_observed']
(ref / 'normal-wake-validation.json').write_text(json.dumps(report, indent=2) + '\n')
(out / 'parsed-wake-events-private.json').write_text(json.dumps(events, indent=2) + '\n')
print(json.dumps(report, indent=2))
