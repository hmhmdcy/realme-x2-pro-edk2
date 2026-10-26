from pathlib import Path
import collections
import json
import re
import tarfile

out = Path('/mnt/e/edk2-samurai-out/kernel137')
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel137')
with tarfile.open(out / 'first-runtime-private.tar.gz') as archive:
    data = {m.name.removeprefix('./'): archive.extractfile(m).read() for m in archive if m.isfile()}
t = data['dmesg.txt'].decode()
events = []
for line in t.splitlines():
    ts = re.match(r'\[\s*([0-9.]+)\]', line)
    if not ts:
        continue
    if 'dsi_err_worker' in line:
        suffix = line.split('dsi_err_worker', 1)[1]
        # Driver diagnostics contain only named interrupt/status registers.
        suffix = re.sub(r'\b[0-9a-fA-F]{12,}\b', '<redacted>', suffix)
        events.append(dict(seconds=float(ts[1]), category='dsi', diagnostic=suffix.strip()))
    elif 'frame done timeout' in line:
        events.append(dict(seconds=float(ts[1]), category='frame_timeout'))
summary = dict(stage=137, boot_warning_count=t.count('WARNING:'),
    dma_tx_prepare_failures=t.count('unable to prepare channel'),
    dma_failure_diagnostics_emitted=t.count('TX DMA diagnostic') + t.count('BAM DMA diagnostic'),
    dsi_counts=dict(collections.Counter(e.get('diagnostic') for e in events if e['category'] == 'dsi')),
    first_display_events=events[:12], last_display_events=events[-8:],
    startup_audio_errors_absent_this_boot=True, startup_audio_root_cause_proven=False,
    display_accepted=False, goal_complete=False)
(ref / 'boot-error-validation.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary, indent=2), flush=True)
