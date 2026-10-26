#!/usr/bin/env python3
"""Verify the missing-pending boundary from raw RX44 evidence."""
from hashlib import sha256
from pathlib import Path
import re

BASE = Path(__file__).resolve().parent
for row in (BASE / 'SHA256SUMS').read_text().splitlines():
    expected, name = row.split('  ', 1)
    assert sha256((BASE / name).read_bytes()).hexdigest() == expected, name

def decode(name):
    raw = (BASE / (name + '.raw')).read_bytes()
    text = bytearray()
    pos = frames = 0
    while pos < len(raw):
        assert pos + 1 < len(raw) and raw[pos] == 0x90, (name, pos)
        length = raw[pos + 1]
        assert 1 <= length <= 64 and pos + length + 2 <= len(raw), (name, pos)
        text.extend(raw[pos + 2:pos + length + 2])
        pos += length + 2
        frames += 1
    print(f'{name}: {frames} complete frames, {len(raw)} raw bytes')
    return text.decode('ascii', errors='replace')

for name in ('stats-boot', 'stats-ctrl-u-boot', 'final-boot'):
    text = decode(name)
    assert 'AHB2PHY TOP_CFG=00000011 original=00000000' in text
    assert '[tty] shell started on /dev/ttyEUD0' in text
for name in ('metrics-before', 'native-a', 'native-b', 'stats-var-2', 'stats-var-again-1'):
    assert decode(name) == '', name

def metrics(name):
    line = re.search(r'eud: tty byte=15 (.+)', decode(name)).group(1)
    fields = {key: int(value) for key, value in re.findall(r'(\w+)=(\d+)', line)}
    for field in ('bad', 'no_tty', 'overrun', 'bad_id', 'bad_len'):
        assert fields[field] == 0, (name, field)
    assert fields['pending'] == fields['frames'], name
    assert fields['bytes'] == fields['tty_before'] + 1, name
    return fields

a = metrics('metrics-recovery')
b = metrics('metrics-after-b')
c = metrics('metrics-after-c')
assert (a['pending'], a['frames'], a['bytes'], a['tty_before']) == (1, 1, 1, 0)
assert (b['pending'], b['frames'], b['bytes'], b['tty_before']) == (2, 2, 2, 1)
assert (c['pending'], c['frames'], c['bytes'], c['tty_before']) == (4, 4, 13, 12)
assert a['polls'] < b['polls'] < c['polls']
assert b['pending'] - a['pending'] == 1, 'Failed B input must not add a pending observation'
assert c['bytes'] - b['bytes'] == 11, 'Successful C payload plus Ctrl-U'
positive = decode('native-c-positive-control')
assert 'data=65 63 68 6f 20 52 34 34 43 0a s1_after=06060606' in positive
assert re.search(r'\r?\nR44C\r?\n~ # ', positive)
assert 'reboot2 bootloader requested' in decode('final-f1')
assert 'product: msmnile' in (BASE / 'final-fastboot-product.txt').read_text()
metrics('final-live-ctrl-u')
assert all('Writing \'logdump\'' in (BASE / name).read_text() for name in ('flash-stats.txt', 'flash-stats-ctrl-u.txt'))
print('PASS: counters distinguish missing pending from header/tty loss; native output and F1 retained.')
print('Not proof of why pending was absent, or of lossless TX/reliable native delivery.')
