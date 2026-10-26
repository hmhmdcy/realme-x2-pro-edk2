#!/usr/bin/env python3
"""Verify saved RX43 evidence without inferring receipt from USB completion."""
import json
from pathlib import Path
import re

BASE = Path(__file__).resolve().parent


def decode(name):
    raw = (BASE / (name + '.raw')).read_bytes()
    output = bytearray()
    offset = frames = stray = 0
    while offset + 1 < len(raw):
        size = raw[offset + 1]
        if raw[offset] != 0x90 or not 1 <= size <= 64:
            offset += 1
            stray += 1
            continue
        if offset + size + 2 > len(raw):
            break
        output.extend(raw[offset + 2:offset + 2 + size])
        offset += size + 2
        frames += 1
    print(f'{name}: bytes={len(raw)} frames={frames} stray={stray} pending={len(raw)-offset}')
    assert stray == 0 and offset == len(raw), name
    return output.decode('ascii', errors='replace')


for name in ('baseline-boot', 'final-boot'):
    text = decode(name)
    assert 'AHB2PHY TOP_CFG=00000011 original=00000000' in text, name
    assert '[tty] shell started on /dev/ttyEUD0' in text, name

for name, command, marker in (
    ('libusb-native-b', b'echo R43B\n', 'R43B'),
    ('native-echo-c', b'echo R43C\n', 'R43C'),
    ('final-native-echo', b'echo R43F\n', 'R43F'),
):
    text = decode(name)
    assert f'rx frame len={len(command)} data={command.hex(" ")}' in text, name
    assert re.search(r'\r?\n' + marker + r'\r?\n~ # ', text), name

prefix = decode('native-console-prefix')
suffix = decode('native-console-suffix')
assert 'data=65 63 68 6f 20 52 34 33 44 3e' in prefix
assert 'data=2f 64 65 76 2f 63 6f 6e 73 6f 6c 65 0a' in suffix
assert re.search(r'\r?\nR43D\r?\n~ # ', suffix)

for name in ('native-echo-a', 'libusb-stty'):
    assert (BASE / (name + '.raw')).stat().st_size == 0, name

tail = decode('libusb-dmesg-tail')
assert '[  138.505537] eud: tty byte=15' in tail
assert '[  240.242865] eud: tty byte=15' in tail
assert 'data=65 63 68 6f 20 52 34 33 42 0a' in tail
assert 'data=65 63 68 6f 20 52 34 33 41 0a' not in tail
assert '~ # ' in tail
stty = decode('compatible-stty')
assert 'icanon' in stty and 'icrnl' in stty and '~ # ' in stty
assert 'eud: reboot2 bootloader requested' in decode('f1')
assert 'product: msmnile' in (BASE / 'f1-fastboot.txt').read_text(encoding='utf-8-sig')

for name, expected_receipt, length in (
    ('libusb-native-b', True, 12), ('libusb-stty', False, 10),
):
    events = [json.loads(line) for line in (BASE / (name + '.events.jsonl')).read_text().splitlines()]
    complete = [row for row in events if row['event'] == 'out_complete']
    assert len(complete) == 3 and all(row['length'] == length for row in complete), name
    assert events[-1]['event'] == 'finished'
    assert events[-1]['receipt'] is expected_receipt
    trace = (BASE / (name + '.usbmon')).read_text()
    submissions = re.findall(r'^([0-9a-f]+) \d+ S Bo:\d+:\d+:2 -115 ' + str(length) + r' = (.+)$', trace, re.M)
    assert len(submissions) == 3, name
    metadata = json.loads((BASE / (name + '.json')).read_text())
    for urb, payload in submissions:
        assert bytes.fromhex(payload) == bytes.fromhex(metadata['frame']), name
        assert re.search(r'^' + urb + r' \d+ C Bo:\d+:\d+:2 0 ' + str(length) + r' >$', trace, re.M), name
    assert metadata['setup'] is None and not metadata['explicit_out_zlp']

qemu = json.loads((BASE / 'qemu-pty.json').read_text())
assert qemu['one_write_bytes'] == 15 and qemu['cursor_query_seen']
assert not qemu['cursor_response_sent']
assert all(not value for value in qemu['active_lineedit_termios'].values())
assert '\r\nOFFLINE43\r\n' in qemu['output']
print('PASS: native payload/output, console, compatible tty, F1 and bounded USB evidence')
print('Empty captures remain unconfirmed; zero stray is not lossless delivery.')
