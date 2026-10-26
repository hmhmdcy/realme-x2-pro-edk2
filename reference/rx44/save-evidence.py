#!/usr/bin/env python3
"""Publish RX44 captures byte-for-byte, with normalized derivative text."""
from hashlib import sha256
from pathlib import Path
import shutil

SOURCE = Path('/mnt/e/edk2-samurai-out/rx44')
DEST = Path(__file__).resolve().parent
captures = (
    'pre-diagnostic-ctrl-u', 'pre-diagnostic-ctrl-u-recovery',
    'pre-diagnostic-f1', 'stats-boot', 'stats-var-1', 'stats-var-2',
    'first-stats-compatible', 'stats-clear', 'stats-var-again-1',
    'stats-to-ctrl-u-f1', 'stats-ctrl-u-boot', 'metrics-before', 'native-a',
    'metrics-recovery', 'native-b', 'metrics-after-b',
    'native-c-positive-control', 'metrics-after-c', 'final-f1',
    'final-boot', 'final-live-ctrl-u',
)
for name in captures:
    for extension in ('.raw', '.txt', '.events.txt'):
        source = SOURCE / (name + extension)
        destination = DEST / source.name
        if extension == '.raw':
            shutil.copyfile(source, destination)
            assert source.read_bytes() == destination.read_bytes()
        else:
            data = source.read_text(encoding='utf-8-sig')
            normalized = '\n'.join(line.rstrip() for line in data.splitlines()).rstrip()
            destination.write_text(normalized + ('\n' if normalized else ''), encoding='utf-8')
for name in ('pre-flash-product.txt', 'pre-ctrl-u-flash-product.txt',
             'final-fastboot-product.txt', 'flash-stats.txt',
             'flash-stats-ctrl-u.txt', 'diagnostic-hashes.txt', 'ctrl-u-hashes.txt'):
    data = (SOURCE / name).read_text(encoding='utf-8-sig')
    normalized = '\n'.join(line.rstrip() for line in data.splitlines()).rstrip()
    (DEST / name).write_text(normalized + ('\n' if normalized else ''), encoding='utf-8')
rows = [f'{sha256(p.read_bytes()).hexdigest()}  {p.name}\n' for p in sorted(DEST.glob('*.raw'))]
(DEST / 'SHA256SUMS').write_text(''.join(rows), encoding='ascii')
print(f'Copied {len(captures)} capture sets; raw hashes retained.')
