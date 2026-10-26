#!/usr/bin/env python3
"""Export RX46 raw evidence and exact tested sources without device access."""
from hashlib import sha256
from pathlib import Path
import shutil

SOURCE = Path('/mnt/e/edk2-samurai-out/rx46')
DEST = Path(__file__).resolve().parent
windows = (
    'baseline-live-ctrl-u', 'baseline-f1', 'irq-boot', 'irq-native-a',
    'irq-metrics-after-a', 'irq-native-id', 'irq-native-b', 'irq-metrics-after-b',
    'irq-native-c', 'irq-metrics-after-c', 'irq-f1', 'irq-b-boot',
    'irq-b-native-h', 'irq-b-metrics-after-h', 'irq-b-f1', 'final-boot',
    'final-live-ctrl-u', 'etw-before-ctrl-u', 'etw-before-ctrl-u-retry',
    'etw-r46g-capture.native', 'etw-r46g-capture.metrics',
)
usb = ('libusb-native-d-ready', 'libusb-native-e',
       'libusb-native-f-full', 'libusb-metrics-after-f')
protected = []

def exact(name):
    source, destination = SOURCE / name, DEST / name
    shutil.copyfile(source, destination)
    assert source.read_bytes() == destination.read_bytes()
    protected.append(destination)

def normalized(name):
    raw = (SOURCE / name).read_bytes()
    data = raw.decode('utf-16' if raw.startswith(b'\xff\xfe') else 'utf-8-sig')
    text = '\n'.join(line.rstrip() for line in data.splitlines()).rstrip()
    (DEST / name).write_text(text + ('\n' if text else ''), encoding='utf-8')

for name in windows:
    exact(name + '.raw')
    normalized(name + '.txt')
    normalized(name + '.events.txt')
for name in usb:
    for extension in ('.raw', '.usbmon', '.json', '.events.jsonl'):
        exact(name + extension)
    normalized(name + '.txt')
for name in ('eud-before-rx46.c', 'eud-irq-candidate.c', 'eud-irq-candidate-b.c'):
    exact(name)
for name in ('etw-eud-selected.xml', 'etw-eud-summary.json'):
    exact(name)
normalized('etw-r46g-capture.manifest.json')
protected.append(DEST / 'etw-r46g-capture.manifest.json')
for name in ('baseline-fastboot-product.txt', 'pre-flash-product.txt',
             'irq-fastboot-product.txt', 'irq-b-fastboot-product.txt',
             'flash-irq.txt', 'flash-irq-b.txt', 'irq-hashes.txt',
             'irq-b-hashes.txt', 'build-irq.log', 'build-irq-b.log',
             'build-irq-api-error.log', 'etw-preflight.txt',
             'build-irq.sh', 'build-irq-b.sh', 'fastboot-step.ps1',
             'usbmon-preflight.sh', 'authorized-etw-operator.log',
             'etw-r46g-capture.trace-log.txt', 'run-authorized-etw.ps1'):
    normalized(name)
(DEST / 'SHA256SUMS').write_text(''.join(
    f'{sha256(p.read_bytes()).hexdigest()}  {p.name}\n'
    for p in sorted(protected)), encoding='ascii')
print(f'Exported {len(windows) + len(usb)} raw capture sets; exact USB traces and sources retained.')
