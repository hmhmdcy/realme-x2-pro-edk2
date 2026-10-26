from pathlib import Path
import collections
import hashlib
import json
import re
import tarfile
out = Path('/mnt/e/edk2-samurai-out/kernel141')
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel141')
with tarfile.open(out / 'reboot140-startup-private.tar.gz') as archive:
    data = {m.name.removeprefix('./'): archive.extractfile(m).read() for m in archive if m.isfile()}
for line in data['SHA256SUMS'].decode().splitlines():
    digest, name = line.split('  ', 1)
    assert hashlib.sha256(data[name.removeprefix('./')]).hexdigest() == digest
def parse(text):
    result = []
    for line in text.splitlines():
        match = re.search(r'\[(\d+)\].*?\s(\d+\.\d+):\s+([a-zA-Z0-9_]+):\s*(.*)$', line)
        if match:
            result.append(dict(cpu=int(match.group(1)), seconds=float(match.group(2)), name=match.group(3), body=match.group(4)))
    return result
events = parse(data['default-display-early-private.txt'].decode())
stats = json.loads(data['default-display-early-stats-private.json'])
loss = {cpu: {name: int(re.search(r'^' + name + r': (\d+)$', text, re.M).group(1))
              for name in ['overrun', 'commit overrun', 'dropped events']}
        for cpu, text in stats.items()}
timeouts = [e for e in events if e['name'] == 'dpu_enc_frame_done_timeout']
report = dict(stage=141, kernel_build=140, same_new_boot_archive=True,
    early_default_events=dict(collections.Counter(e['name'] for e in events)), early_default_loss=loss,
    early_default_loss_free=not any(v for cpu in loss.values() for v in cpu.values()),
    early_timeout_events=len(timeouts), goal_complete=False)
windows = []
for timeout in timeouts:
    selected = [e for e in events if timeout['seconds'] - 0.13 <= e['seconds'] <= timeout['seconds'] + 0.1]
    windows.append(selected)
(ref / 'early-startup-validation.json').write_text(json.dumps(report, indent=2) + '\n')
(out / 'early-startup-timeout-windows-private.json').write_text(json.dumps(windows, indent=2) + '\n')
print(json.dumps(report, indent=2))
for window in windows:
    stamp = next(e['seconds'] for e in window if e['name'] == 'dpu_enc_frame_done_timeout')
    for e in window:
        if e['name'] in ['dpu_enc_frame_watchdog', 'dpu_enc_frame_done_timeout', 'dpu_enc_frame_done_cb',
                         'dpu_enc_phys_cmd_pp_tx_done', 'dpu_crtc_vblank_cb', 'dpu_enc_trigger_start',
                         'dpu_enc_rc', 'msm_atomic_commit_tail_finish', 'dpu_enc_irq_wait_success']:
            print(round((e['seconds'] - stamp) * 1000, 3), e['cpu'], e['name'],
                  re.sub(r'\b(?:0x)?[0-9a-f]{8,16}\b', '[redacted]', e['body']))
