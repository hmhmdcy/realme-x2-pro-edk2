#!/usr/bin/env python3
"""Check saved hardware receipts; do not infer delivery from host writes."""
from pathlib import Path
import re

BASE = Path(__file__).resolve().parent


def decode(name):
    raw = (BASE / (name + '.raw')).read_bytes()
    parts = []
    offset = frames = stray = 0
    while offset + 1 < len(raw):
        size = raw[offset + 1]
        if raw[offset] != 0x90 or not 1 <= size <= 64:
            offset += 1
            stray += 1
            continue
        if offset + 2 + size > len(raw):
            break
        parts.append(raw[offset + 2:offset + 2 + size])
        offset += size + 2
        frames += 1
    print(f'{name}: bytes={len(raw)} frames={frames} stray={stray} pending={len(raw)-offset}')
    return b''.join(parts).decode('ascii', errors='replace')


for name in ('wait-native', 'wait-native-repeat'):
    text = decode(name)
    assert 'original=00000000 applied=00000011 confirm=00000011' in text
    assert 'RESTORE expected=00000000 readback=00000000' in text
    for label, expected in (('ABC', b'ABC'), ('DEFG', b'DEFG')):
        match = re.search(r'RX41-WAIT RESULT ' + label + r'[^\n]*words=([^\r\n]+)', text)
        assert match, (name, label)
        words = [int(word, 16) for word in match[1].split()]
        assert bytes(word & 0xff for word in words) == expected, (name, label)

for name, expected in (
    ('linux-abc-1', b'ABC'), ('linux-abc-2', b'ABC'),
    ('linux-defg-1', b'DEFG'), ('linux-defg-2-jitter', b'DEFG'),
    ('linux-defg-3', b'DEFG'),
):
    text = decode(name)
    values = re.findall(r'eud: byte\[\d+/\d+\]=([0-9a-f]{2})', text)
    assert bytes(int(value, 16) for value in values) == expected, name
    assert 's1_after=06060606' in text, name

for name in ('linux-defg-2', 'linux-defg-2-retry', 'linux-abc-3'):
    assert (BASE / (name + '.raw')).stat().st_size == 0, name

print('PASS: accepted UEFI/Linux native payloads match; empty captures stay inconclusive')

native = decode('bulk-native-set-x-retry')
assert 'data=58 3d 6f 6b 0a' in native and 'tty=5 id=90' in native
assert re.search(r'\r?\nok\r?\n', decode('bulk-check-x-after-ack'))
for name in ('native-id', 'native-id-cr', 'bulk-native-id', 'ordered-native-id'):
    text = decode(name)
    assert re.search(r'\r?\nuid=0 gid=0\r?\n~ # ', text), name
assert re.search(r'\r?\nRX41-TTY\r?\n~ # ', decode('native-echo-14'))
assert re.search(r'\r?\nRX41-C\r?\n~ # ', decode('ordered-console-native-suffix'))
assert re.search(r'\r?\nE\r?\n', decode('ordered-legacy-echo-e'))
assert re.search(r'\r?\nC\r?\n', decode('ordered-console-legacy-retry'))
assert 'eud: reboot2 bootloader requested' in decode('f1-final-ordered')
assert 'eud: tty byte=15' in decode('final-ctrl-u-retry')
assert (BASE / 'final-ctrl-u.raw').stat().st_size == 0
print('PASS: native shell state effect, compatible terminal/console and F1 receipt')
print('PASS: RX43 audit confirms RX41 native command/console outputs in unchanged raw files')
