#!/usr/bin/env python3
"""Export RX45 evidence without accessing hardware."""
from hashlib import sha256
from pathlib import Path
import shutil

SOURCE = Path('/mnt/e/edk2-samurai-out/rx45')
DEST = Path(__file__).resolve().parent
captures = (
    'baseline-ctrl-u', 'baseline-f1', 'mask-metrics-before',
    'mask-native-a', 'mask-metrics-after-a', 'mask-native-positive',
    'mask-metrics-after-positive', 'mask-f1', 'baseline-return-boot',
    'baseline-return-ctrl-u',
)
for name in (*captures, 'mask-boot'):
    original = name + '.raw' if name == 'mask-boot' else name
    for extension in ('.raw', '.txt', '.events.txt'):
        source = SOURCE / (original + extension)
        destination = DEST / (name + extension)
        if extension == '.raw':
            shutil.copyfile(source, destination)
            assert source.read_bytes() == destination.read_bytes()
        else:
            data = source.read_text(encoding='utf-8-sig')
            normalized = '\n'.join(line.rstrip() for line in data.splitlines()).rstrip()
            destination.write_text(normalized + ('\n' if normalized else ''), encoding='utf-8')
for name in ('baseline-fastboot-product.txt', 'mask-fastboot-product.txt',
             'flash-mask.txt', 'flash-baseline.txt', 'mask-hashes.txt',
             'build-mask.log', 'build-mask.sh', 'fastboot-step.ps1'):
    data = (SOURCE / name).read_text(encoding='utf-8-sig')
    normalized = '\n'.join(line.rstrip() for line in data.splitlines()).rstrip()
    (DEST / name).write_text(normalized + ('\n' if normalized else ''), encoding='utf-8')
shutil.copyfile(SOURCE / 'eud-mask-candidate.c', DEST / 'eud-mask-candidate.c')
shutil.copyfile(SOURCE / 'eud-before-rx45.c', DEST / 'eud-before-rx45.c')
protected = sorted([*DEST.glob('*.raw'), DEST / 'eud-mask-candidate.c', DEST / 'eud-before-rx45.c'])
(DEST / 'SHA256SUMS').write_text(''.join(
    f'{sha256(p.read_bytes()).hexdigest()}  {p.name}\n' for p in protected), encoding='ascii')
print(f'Exported {len(captures) + 1} raw capture sets and exact tested diagnostic.')
