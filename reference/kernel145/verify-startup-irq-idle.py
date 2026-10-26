"""Validate streaming capture and keep bounded timeout windows private."""
from pathlib import Path
import collections
import hashlib
import json
import re
import tarfile

ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel145')
out = Path('/mnt/e/edk2-samurai-out/kernel145')
path = out / 'first145-startup-private.tar.gz'
small = {}
hashes = {}
counter = collections.Counter()
selected = []
rolling = collections.deque()
windows = []
irq_stacks = collections.defaultdict(list)
irq_durations = collections.defaultdict(list)
last_idle = {}
orphan_exits = 0
pattern = re.compile(rb'\[(\d+)\].*?\s(\d+\.\d+):\s+([A-Za-z0-9_]+):\s*(.*)$')

def consume(line):
    global orphan_exits
    match = pattern.search(line)
    if not match:
        return
    event = dict(cpu=int(match.group(1)), seconds=float(match.group(2)),
                 name=match.group(3).decode(), body=match.group(4).decode(errors='replace'))
    name, body, cpu, stamp = event['name'], event['body'], event['cpu'], event['seconds']
    counter[name] += 1
    if name.startswith('dpu_') or name.startswith('msm_gpu_') or name.startswith('msm_atomic_') or name.startswith('msm_dsi_'):
        selected.append(event)
    while rolling and rolling[0]['seconds'] < stamp - 0.18:
        rolling.popleft()
    rolling.append(event)
    for window in windows:
        if window['timeout_seconds'] < stamp <= window['timeout_seconds'] + 0.12:
            window['events'].append(event)
    if name == 'irq_handler_entry':
        irq = int(re.search(r'irq=(\d+)', body).group(1))
        irq_stacks[cpu].append(dict(irq=irq, name=body.split(' name=', 1)[-1], seconds=stamp))
    elif name == 'irq_handler_exit':
        irq = int(re.search(r'irq=(\d+)', body).group(1))
        if irq_stacks[cpu] and irq_stacks[cpu][-1]['irq'] == irq:
            start = irq_stacks[cpu].pop()
            row = dict(start, cpu=cpu, end_seconds=stamp, duration_ms=round((stamp - start['seconds']) * 1000, 6))
            irq_durations[cpu].append(row)
        else:
            orphan_exits += 1
    elif name == 'cpu_idle':
        state = int(re.search(r'state=(\d+)', body).group(1))
        target = int(re.search(r'cpu_id=(\d+)', body).group(1))
        last_idle[target] = dict(state=state, seconds=stamp)
    elif name == 'dpu_enc_frame_done_timeout':
        windows.append(dict(timeout_seconds=stamp, timeout_body=body, events=list(rolling),
            inflight_irq_at_timeout={str(key): [dict(item) for item in value] for key, value in irq_stacks.items() if value},
            last_idle_at_timeout={str(key): dict(value) for key, value in last_idle.items()}))

with tarfile.open(path) as archive:
    seen = set()
    for member in archive:
        assert not member.issym() and not member.islnk()
        if not member.isfile():
            continue
        name = member.name.removeprefix('./')
        assert not Path(name).is_absolute() and '..' not in Path(name).parts and name not in seen
        seen.add(name)
        stream = archive.extractfile(member)
        digest = hashlib.sha256()
        if name == 'startup-stream-private.txt':
            for line in stream:
                digest.update(line)
                consume(line)
        else:
            content = stream.read()
            digest.update(content)
            small[name] = content
        hashes[name] = digest.hexdigest()
for line in small['SHA256SUMS'].decode().splitlines():
    digest, name = line.split('  ', 1)
    assert hashes[name.removeprefix('./')] == digest
assert small['boot-id-private.txt'] != (out / 'source-boot-id-private.txt').read_bytes()
report = json.loads(small['startup-result.json'])
assert report['same_new_boot'] and report['new_boot'] and report['current_kernel'] == 145
assert report['error'] is None and report['trace_stream_reader_errors'] == []
assert report['trace_instance_removed'] and report['early_boot_service']
assert report['no_output_or_application_workload_requested']
stats = json.loads(small['trace-stats-private.json'])
loss = {cpu: {name: int(re.search(r'^' + name + r': (\d+)$', text, re.M).group(1))
              for name in ['overrun', 'commit overrun', 'dropped events']}
        for cpu, text in stats.items()}
assert len(stats) == 8
loss_free = not any(number for cpu in loss.values() for number in cpu.values())
# Any final non-streamed events remain evidence, with no invented loss-free claim.
for line in small['startup-trace-private.txt'].splitlines(keepends=True):
    consume(line)
selected.sort(key=lambda item: item['seconds'])
summaries = []
for window in windows:
    stamp = window['timeout_seconds']
    identifier = int(re.search(r'id=(\d+)', window['timeout_body']).group(1))
    arm = next((event for event in reversed(selected) if event['seconds'] < stamp
        and event['name'] == 'dpu_enc_frame_watchdog' and 'action=arm ' in event['body']
        and re.search(r'\bid=' + str(identifier) + r'\b', event['body'])), None)
    pp = next((event for event in selected if event['seconds'] > stamp
        and event['name'] == 'dpu_enc_phys_cmd_pp_tx_done'
        and re.search(r'\bid=' + str(identifier) + r'\b', event['body'])), None)
    start = arm['seconds'] if arm else stamp - 0.083
    items = sorted([event for event in window['events'] if start <= event['seconds'] <= stamp], key=lambda event: event['seconds'])
    inflight = [dict(cpu=int(cpu), duration_to_timeout_ms=round((stamp - item['seconds']) * 1000, 3))
                for cpu, entries in window['inflight_irq_at_timeout'].items() for item in entries]
    summary = dict(timeout_trace_seconds=stamp, complete_arm_recorded=arm is not None,
        pp_done_callback_after_timeout_recorded=pp is not None,
        arm_to_timeout_ms=round((stamp - start) * 1000, 3),
        arm_to_pp_done_callback_ms=round((pp['seconds'] - start) * 1000, 3) if pp else None,
        irq_entries_cpu0_before_timeout=sum(event['name'] == 'irq_handler_entry' and event['cpu'] == 0 for event in items),
        cpu_idle_events_cpu0_before_timeout=sum(event['name'] == 'cpu_idle' and event['cpu'] == 0 for event in items),
        gpu_retire_events_before_timeout=sum(event['name'] == 'msm_gpu_submit_retired' for event in items),
        inflight_irq_at_timeout=inflight)
    summaries.append(summary)
samples = json.loads(small['startup-samples-private.json'])
report.update(archive_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), archive_manifest_verified=True,
    trace_stream_loss_free=loss_free, trace_loss=loss, events=dict(counter),
    first_sample_uptime_seconds=samples[0]['uptime_seconds'],
    last_sample_uptime_seconds=samples[-1]['uptime_seconds'],
    own_timeout_events=len(windows), complete_timeout_arm_records=sum(row['complete_arm_recorded'] for row in summaries),
    timeout_summaries=summaries, unpaired_irq_exits=orphan_exits,
    max_completed_irq_handler_duration_ms_by_cpu={str(cpu): max(row['duration_ms'] for row in rows) for cpu, rows in irq_durations.items()},
    cpu_idle_exit_trace_is_not_direct_hardware_wakeup_timestamp=True,
    pp_trace_new_count_is_atomic_operation_boolean=True,
    display_fix_proven=False, gpu_and_charging_acceptance_pending=True, goal_complete=False)
enabled = set(json.loads(small['enabled-events.json']))
expected_dsi = {'events/drm_msm_dsi/' + name + '/enable' for name in ['msm_dsi_error_irq', 'msm_dsi_error_status', 'msm_dsi_error_work']}
assert expected_dsi <= enabled
report.update(three_new_dsi_tracepoints_enabled=True, raw_dsi_events_retained_private=True, dsi_event_counts={name:counter[name] for name in ['msm_dsi_error_irq', 'msm_dsi_error_status', 'msm_dsi_error_work']})
(ref / 'startup-irq-idle-validation.json').write_text(json.dumps(report, indent=2) + '\n')
(out / 'timeout-irq-idle-windows-private.json').write_text(json.dumps(windows, indent=2) + '\n')
(out / 'selected-startup-events-private.json').write_text(json.dumps(selected, indent=2) + '\n')
(out / 'long-irq-handlers-private.json').write_text(json.dumps({str(cpu): sorted(rows, key=lambda row: row['duration_ms'], reverse=True)[:25]
    for cpu, rows in irq_durations.items()}, indent=2) + '\n')
(out / 'new-boot-id-private.txt').write_bytes(small['boot-id-private.txt'])
print(json.dumps(report, indent=2))
