#!/usr/bin/env python3
"""Verify RX45's limited mask result from raw captures and counters."""
from hashlib import sha256
from pathlib import Path
import re

BASE = Path(__file__).resolve().parent
for row in (BASE / 'SHA256SUMS').read_text().splitlines():
    expected, name = row.split('  ', 1)
    assert sha256((BASE / name).read_bytes()).hexdigest() == expected, name

def decode(name, expected_stray=0):
    raw = (BASE / (name + '.raw')).read_bytes()
    text = bytearray()
    pos = frames = stray = 0
    while pos + 1 < len(raw):
        length = raw[pos + 1]
        if raw[pos] != 0x90 or not 1 <= length <= 64:
            pos += 1
            stray += 1
            continue
        assert pos + length + 2 <= len(raw), (name, pos, 'incomplete frame')
        text.extend(raw[pos + 2:pos + length + 2])
        pos += length + 2
        frames += 1
    assert pos == len(raw), (name, 'trailing bytes')
    assert stray == expected_stray, (name, stray)
    print(f'{name}: frames={frames}, stray={stray}, raw={len(raw)}')
    return text.decode('ascii', errors='replace')

boot = decode('mask-boot', 8)
assert 'AHB2PHY TOP_CFG=00000011 original=00000000' in boot
assert 'RX45 INT1 mask=1d original=1c (polling retained)' in boot
assert '[tty] shell started on /dev/ttyEUD0' in boot
assert decode('mask-native-a') == ''

def metrics(name):
    line = re.search(r'eud: tty byte=15 (.+)', decode(name)).group(1)
    fields = {key: int(value) for key, value in re.findall(r'(\w+)=(\d+)', line)}
    for key in ('bad', 'no_tty', 'overrun', 'bad_id', 'bad_len'):
        assert fields[key] == 0, (name, key)
    assert fields['pending'] == fields['frames']
    assert fields['bytes'] == fields['tty_before'] + 1
    return fields

a = metrics('mask-metrics-before')
b = metrics('mask-metrics-after-a')
c = metrics('mask-metrics-after-positive')
assert (a['polls'], a['pending'], a['frames'], a['bytes'], a['tty_before']) == (2847, 1, 1, 1, 0)
assert (b['polls'], b['pending'], b['frames'], b['bytes'], b['tty_before']) == (4784, 2, 2, 2, 1)
assert (c['polls'], c['pending'], c['frames'], c['bytes'], c['tty_before']) == (6327, 4, 4, 17, 16)
assert b['pending'] - a['pending'] == 1, 'Failed native input adds no observed pending'
assert c['bytes'] - b['bytes'] == 15, 'One 14-byte command and the snapshot byte'
positive = decode('mask-native-positive')
assert 'len=14 data=65 63 68 6f 20 52 34 35 42 31 32 33 34 0a s1_after=06060606' in positive
assert re.search(r'\r?\nR45B1234\r?\n~ # ', positive)
for name in ('baseline-f1', 'mask-f1'):
    assert 'reboot2 bootloader requested' in decode(name)
for name in ('baseline-fastboot-product.txt', 'mask-fastboot-product.txt'):
    assert 'product: msmnile' in (BASE / name).read_text()
for name in ('flash-mask.txt', 'flash-baseline.txt'):
    assert "Writing 'logdump'" in (BASE / name).read_text()
returned = decode('baseline-return-boot')
assert 'AHB2PHY TOP_CFG=00000011 original=00000000' in returned
assert '[tty] shell started on /dev/ttyEUD0' in returned
assert 'RX45 INT1 mask=' not in returned
metrics('baseline-ctrl-u')
metrics('baseline-return-ctrl-u')
assert sha256((BASE / 'eud-before-rx45.c').read_bytes()).hexdigest() == 'e17acbd5d6139c94c3e22f6d6bcd442186d3bd24e9292a10e29f3d5781970dd2'
assert sha256((BASE / 'eud-mask-candidate.c').read_bytes()).hexdigest() == 'a4a51107234b38140e2e64dfd79f665af97e9f5aa5689748207c5a769fae9b2c'
print('PASS: persistent RX mask alone is insufficient; exact payload/output and F1 retained; baseline restored.')
print('This run does not verify IRQ delivery, pending lifetime, physical USB OUT or reliable native delivery.')
