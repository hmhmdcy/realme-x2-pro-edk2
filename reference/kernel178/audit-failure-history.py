from pathlib import Path
import json, re, tarfile

ref = Path(__file__).resolve().parent
archive = Path('E:/edk2-samurai-out/kernel178/k178-all-private.tar.gz')
paths = ['k178-adsp-restart/dmesg-before-private.txt', 'k178-adsp-restart/dmesg-after-private.txt',
         'k178-adsp-restart/postfailure-current-dmesg-private.txt', 'k178-final/dmesg-current-private.txt']
patterns = {'irq_read_not_connected': 'Failed to read IRQ status: -107', 'irq_config_failed': 'Failed to write config',
            'irq_mask_sync_failed': 'Failed to sync masks', 'asoc_error': 'ASoC error',
            'pdr_listener_timeout': 'register listener txn wait failed'}
found = {k: set() for k in patterns}
before = {k: set() for k in patterns}
with tarfile.open(archive) as ar:
    for path in paths:
        for line in ar.extractfile(path).read().decode().splitlines():
            for key, pattern in patterns.items():
                if pattern in line:
                    found[key].add(line)
                    if path.endswith('/dmesg-before-private.txt'): before[key].add(line)
summary = {}
for key, all_rows in found.items():
    rows = all_rows - before[key]
    times = sorted(float(re.match(r'^\[\s*([0-9.]+)\]', line)[1]) for line in rows)
    summary[key] = dict(unique_captured_log_lines=len(rows), first_timestamp=times[0] if times else None,
                        last_timestamp=times[-1] if times else None)
report = dict(stage=178, kernel_build=176, method='Union of timestamped exact log lines across saved snapshots',
              lower_bound_only_due_kernel_ring_overwrite=True, unique_fault_history=summary,
              pre_restart_fault_counts={k: len(v) for k, v in before.items()},
              pdr_timeout_timestamps=sorted(re.match(r'^\[\s*([0-9.]+)\]', line)[1] for line in found['pdr_listener_timeout']-before['pdr_listener_timeout']),
              original_failure_audit_not_replaced=True)
(ref / 'known-failure-history.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report, indent=2))
