"""Inspect trace context and gaps without exposing task IDs or addresses."""
from pathlib import Path
import collections
import json
import re
import tarfile

out = Path('/mnt/e/edk2-samurai-out/kernel142')
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel142')
metadata = json.loads(ref.joinpath('startup-irq-idle-validation.json').read_text())
assert metadata['archive_manifest_verified'] and metadata['trace_stream_loss_free']
window = json.loads(out.joinpath('timeout-irq-idle-windows-private.json').read_text())[0]
timeout = window['timeout_seconds']
items = window['events']
by_cpu = {cpu: sorted([e for e in items if e['cpu'] == cpu], key=lambda e: e['seconds']) for cpu in range(8)}
zero = by_cpu[0]
before = [e for e in zero if timeout - 0.1 <= e['seconds'] <= timeout]
left, right = max(zip(before, before[1:]), key=lambda pair: pair[1]['seconds'] - pair[0]['seconds'])
start, end = left['seconds'], right['seconds']
report = dict(stage=142, kernel_build=140, trace_loss_free=True,
    cpu0_largest_event_gap_ms=round((end-start)*1000, 3),
    gap_begin_before_timeout_ms=round((start-timeout)*1000, 3),
    gap_end_before_timeout_ms=round((end-timeout)*1000, 3),
    last_event_name=left['name'], first_event_name=right['name'],
    other_cpus_event_counts_during_gap={str(cpu): sum(start < e['seconds'] < end for e in events) for cpu, events in by_cpu.items()},
    whole_machine_frozen_proven=False, interrupts_disabled_region_proven=False,
    physical_irq_arrival_timestamp_recorded=False, goal_complete=False)
contexts = []
pattern = re.compile(rb'^\s*(.+?)-\d+\s+\[(\d+)\]\s+(\S+)\s+(\d+\.\d+):\s+([A-Za-z0-9_]+):\s*(.*)$')
with tarfile.open(out / 'reboot140-startup-private.tar.gz') as archive:
    for line in archive.extractfile('./startup-stream-private.txt'):
        match = pattern.search(line)
        if not match or int(match[2]) != 0:
            continue
        stamp = float(match[4])
        if start - 0.00015 <= stamp <= end + 0.0002:
            name = match[5].decode()
            body = re.sub(r'0x[0-9a-fA-F]+|\b[0-9a-fA-F]{12,16}\b', '[address]', match[6].decode(errors='replace'))
            context = dict(relative_to_timeout_ms=round((stamp-timeout)*1000, 3),
                task_name=match[1].decode(errors='replace'), flags=match[3].decode(), event=name,
                body=body if name != 'timer_expire_entry' and name != 'timer_expire_exit' else '[timer details private]')
            contexts.append(context)
report['gap_boundary_trace_context'] = contexts
ref.joinpath('cpu0-event-gap-validation.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))

root = Path('/home/cy122/pmos-samurai-kernel136/kernel')
for name, expression in [('drivers/cpuidle/cpuidle.c', r'trace_cpu_idle|enter_state|local_irq'),
    ('drivers/firmware/qcom/qcom_scm-smc.c', r'raw_spin|spin_lock|arm_smccc|qcom_scm_call'),
    ('drivers/firmware/qcom/qcom_scm.c', r'qcom_scm_pas_auth_and_reset|qcom_scm_pas_init_image'),
    ('drivers/remoteproc/qcom_q6v5_pas.c', r'auth_and_reset|init_image|pas_start')]:
    print(name)
    for number, line in enumerate(root.joinpath(name).read_text().splitlines(),1):
        if re.search(expression, line):
            print(f'{number}: {line}')
