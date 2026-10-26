"""Bounded, address-free view of the validated timeout capture."""
from pathlib import Path
import json
import re
import tarfile

out = Path('/mnt/e/edk2-samurai-out/kernel142')
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel142')
meta = json.loads(ref.joinpath('startup-irq-idle-validation.json').read_text())
assert meta['archive_manifest_verified'] and meta['trace_stream_loss_free']
windows = json.loads(out.joinpath('timeout-irq-idle-windows-private.json').read_text())
for window in windows:
    stamp = window['timeout_seconds']
    print('TIMEOUT', stamp, 'last CPU0 idle:', window['last_idle_at_timeout'].get('0'))
    for event in window['events']:
        delta = (event['seconds'] - stamp) * 1000
        if delta < -105 or delta > 40:
            continue
        name = event['name']
        if name.startswith(('dpu_', 'msm_atomic_')) or (event['cpu'] == 0 and name in
                ['irq_handler_entry', 'irq_handler_exit', 'cpu_idle', 'softirq_entry', 'softirq_exit', 'cpu_frequency']):
            body = re.sub(r'0x[0-9a-fA-F]+|\b[0-9a-fA-F]{12,16}\b', '[address]', event['body'])
            print(f'{delta:9.3f}ms CPU{event["cpu"]} {name} {body}')
long = json.loads(out.joinpath('long-irq-handlers-private.json').read_text())
print('TOP CPU0 HANDLERS', [{key: row[key] for key in ['irq', 'name', 'duration_ms']} for row in long['0'][:8]])
with tarfile.open(out / 'reboot140-startup-private.tar.gz') as archive:
    for filename in ['interrupts-final-private.txt', 'dmesg-early-private.txt', 'dmesg-final-private.txt']:
        content = archive.extractfile('./' + filename).read().decode(errors='replace')
        print(filename)
        for line in content.splitlines():
            if ('interrupts' in filename and re.search(r'mdp|msm|dsi|adreno|arch_timer', line, re.I)) or (
                    'dmesg' in filename and re.search(r'frame done timeout|TX DMA diagnostic|BAM DMA diagnostic|NGD suspend', line)):
                print(re.sub(r'0x[0-9a-fA-F]+|\b[0-9a-fA-F]{12,16}\b', '[address]', line))
