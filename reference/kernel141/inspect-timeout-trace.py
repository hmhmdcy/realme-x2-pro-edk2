from pathlib import Path
import collections
import hashlib
import json
import re
import tarfile

ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel141')
out = Path('/mnt/e/edk2-samurai-out/kernel141')
with tarfile.open(out / 'current140-display-private.tar.gz') as archive:
    data = {m.name.removeprefix('./'): archive.extractfile(m).read() for m in archive if m.isfile()}
for line in data['SHA256SUMS'].decode().splitlines():
    digest, name = line.split('  ', 1)
    assert hashlib.sha256(data[name.removeprefix('./')]).hexdigest() == digest
assert data['boot-id-private.txt'] == (out.parent / 'kernel140/embedded-boot-id-private.txt').read_bytes()
trace = data['display-trace-private.txt'].decode()
events = []
for line in trace.splitlines():
    m = re.search(r'\s(\d+\.\d+):\s+([a-zA-Z0-9_]+):\s*(.*)$', line)
    if m:
        events.append(dict(seconds=float(m.group(1)), name=m.group(2), body=m.group(3), raw=line))
windows = []
for event in events:
    if event['name'] != 'dpu_enc_frame_done_timeout':
        continue
    stamp = event['seconds']
    selected = [e for e in events if stamp - 0.14 <= e['seconds'] <= stamp + 0.07]
    window = dict(timeout_trace_seconds=stamp, event_counts=dict(collections.Counter(e['name'] for e in selected)),
                  event_order=[dict(relative_ms=round((e['seconds'] - stamp) * 1000, 3), name=e['name'],
                       body=re.sub(r'\b(?:0x)?[0-9a-f]{8,16}\b', '[redacted]', e['body']))
                       for e in selected if not e['name'].startswith('tracing_mark')])
    windows.append(window)
    (out / f'timeout-{len(windows)}-window-private.txt').write_text('\n'.join(e['raw'] for e in selected) + '\n')
assert len(windows) == 4
stats = json.loads(data['display-trace-stats-private.json'])
overruns = {cpu: int(re.search(r'^overrun: (\d+)', text, re.M).group(1)) for cpu, text in stats.items()}
report = dict(stage=141, current_kernel=140, same_current_boot_verified=True,
              archive_hash_verified=True, trace_clock=data['display-trace_clock.txt'].decode().strip(),
              trace_overruns=overruns, trace_loss_free=False, all_four_timeout_events_present=True,
              cross_clock_order_not_assumed=True, current_output_enabled=b'Enabled: yes' in data['outputs-current-private.txt'],
              timeout_trace_seconds=[w['timeout_trace_seconds'] for w in windows],
              timeout_event_body=[next(e['body'] for e in w['event_order'] if e['name'] == 'dpu_enc_frame_done_timeout') for w in windows],
              display_fix_not_yet_proven=True, goal_complete=False)
(out / 'timeout-windows-private.json').write_text(json.dumps(windows, indent=2) + '\n')
(ref / 'timeout-trace-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
for i, window in enumerate(windows):
    print('TIMEOUT_WINDOW', i + 1)
    print(json.dumps(window['event_order'][-32:], indent=2))
