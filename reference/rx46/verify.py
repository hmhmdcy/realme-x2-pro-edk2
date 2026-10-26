#!/usr/bin/env python3
"""Verify RX46 IRQ evidence, not native terminal reliability."""
from hashlib import sha256
from pathlib import Path
import json
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
    print(f'{name}: frames={frames}, raw={len(raw)}; no resync/incomplete bytes')
    return text.decode('ascii', errors='replace')

for name in ('irq-boot', 'irq-b-boot', 'final-boot'):
    text = decode(name)
    assert 'AHB2PHY TOP_CFG=00000011 original=00000000' in text
    assert 'RX46 IRQ requested virq=19 hwirq=524 route=legacy-SPI492' in text
    assert 'RX46 IRQ armed virq=19 active=1 mask=01 original=1c' in text
    assert '[tty] shell started on /dev/ttyEUD0' in text
    assert 'RX46 IRQ fallback' not in text

def metrics(name, expected=None):
    line = re.search(r'eud: tty byte=15 (.+)', decode(name)).group(1)
    s = {key: int(value) for key, value in re.findall(r'(\w+)=(\d+)', line)}
    for key in ('bad', 'no_tty', 'overrun', 'bad_id', 'bad_len', 'poll_frames',
                'empty', 'watchdog', 'drops', 'fault'):
        assert s[key] == 0, (name, key, s[key])
    assert s['active'] == 1
    assert s['irqs'] == s['irq_frames'] == s['frames'] == s['pending']
    assert s['bytes'] == s['tty_before'] + 1
    if expected:
        assert (s['polls'], s['frames'], s['bytes'], s['tty_before']) == expected
    return s

a = metrics('irq-metrics-after-a', (3543, 2, 11, 10))
b = metrics('irq-metrics-after-b', (9508, 5, 29, 28))
c = metrics('irq-metrics-after-c', (10819, 6, 30, 29))
assert c['irqs'] - b['irqs'] == c['pending'] - b['pending'] == 1
assert c['bytes'] - b['bytes'] == 1, 'Failed C adds no IRQ/frame/tty; only the snapshot byte'
assert decode('irq-native-c') == ''
events = (BASE / 'irq-native-c.events.txt').read_text()
assert 'sent=1 receipt=False frames=0 stray=0 pending=0' in events
metrics('irq-b-metrics-after-h', (6323, 2, 15, 14))
metrics('final-live-ctrl-u', (6895, 1, 1, 0))

commands = {
    'irq-native-a': 'R46A', 'irq-native-b': 'R46B1234',
    'libusb-native-d-ready': 'R46D', 'libusb-native-e': 'R46E',
    'libusb-native-f-full': 'R46F1234', 'irq-b-native-h': 'R46H1234',
}
for name, word in commands.items():
    text = decode(name)
    payload = ('echo ' + word + '\n').encode()
    assert f'len={len(payload)} data={payload.hex(" ")} s1_after=06060606 via=irq' in text
    assert re.search(r'\r?\n' + word + r'\r?\n~ # ', text)
    if name.startswith('irq-b'):
        assert 'deprecated workqueue' not in text
ident = decode('irq-native-id')
assert 'len=3 data=69 64 0a s1_after=06060606 via=irq' in ident
assert 'uid=0 gid=0' in ident
assert 'deprecated workqueue' in decode('irq-native-a')

lib = metrics('libusb-metrics-after-f', (26680, 10, 65, 64))
assert lib['frames'] - c['frames'] == 4
assert lib['bytes'] - c['bytes'] == 35, 'D10 + E10 + F14 + Ctrl-U1'
for name in (*[n for n in commands if n.startswith('libusb')], 'libusb-metrics-after-f'):
    meta = json.loads((BASE / (name + '.json')).read_text())
    assert meta['read_size'] == 16 and meta['setup'] is None
    assert meta['explicit_out_zlp'] is False
    assert {(ep['address'], ep['max_packet']) for ep in meta['endpoints']} == {(129, 16), (2, 16)}
    event_rows = [json.loads(row) for row in (BASE / (name + '.events.jsonl')).read_text().splitlines()]
    assert [e for e in event_rows if e['event'] == 'finished'][0]['receipt'] is True
    outputs = [e for e in event_rows if e['event'] == 'out_complete']
    assert len(outputs) == 1 and outputs[0]['length'] == len(bytes.fromhex(meta['frame']))
    submissions, completions = {}, {}
    for line in (BASE / (name + '.usbmon')).read_text().splitlines():
        m = re.match(r'^(\S+) \d+ ([SC]) (Bo:\d+:\d+:\d+) (-?\d+) (\d+)(.*)$', line)
        if not m:
            continue
        tag, kind, endpoint, status, length, tail = m.groups()
        if kind == 'S':
            submissions[tag] = (int(length), ''.join(tail.split('=', 1)[1].split()))
        else:
            completions[tag] = (int(status), int(length))
    assert len(submissions) == 1
    tag, (length, payload) = next(iter(submissions.items()))
    assert payload == meta['frame'].replace(' ', '')
    assert completions[tag] == (0, length)
    print(f'{name}: one complete status-zero OUT, length={length}, device receipt present')

for name in ('irq-f1', 'irq-b-f1'):
    text = decode(name)
    assert 'RX46 F1 via=irq' in text and 'fault=0' in text
    assert 'reboot2 bootloader requested' in text
assert 'reboot2 bootloader requested' in decode('baseline-f1')
for name in ('baseline-fastboot-product.txt', 'irq-fastboot-product.txt', 'irq-b-fastboot-product.txt'):
    assert 'product: msmnile' in (BASE / name).read_text()
for name in ('flash-irq.txt', 'flash-irq-b.txt'):
    assert "Writing 'logdump'" in (BASE / name).read_text()
for name in ('build-irq.log', 'build-irq-b.log'):
    assert not re.search(r'warning:|error:', (BASE / name).read_text())
assert 'Access is denied.' in (BASE / 'etw-preflight.txt').read_text()
assert sha256((BASE / 'eud-irq-candidate.c').read_bytes()).hexdigest() == '2666a654225f898f07b8e3696f7ba6cc203ee3d0746ce4bf66286cc190f035cb'
assert sha256((BASE / 'eud-irq-candidate-b.c').read_bytes()).hexdigest() == '673c485843bc551788a0eb90499207371110807d4700a1f3f20d42b76e4e921f'
assert sha256((BASE / 'eud-before-rx46.c').read_bytes()).hexdigest() == 'e17acbd5d6139c94c3e22f6d6bcd442186d3bd24e9292a10e29f3d5781970dd2'
assert decode('etw-before-ctrl-u') == ''
before = metrics('etw-before-ctrl-u-retry', (42611, 2, 2, 1))
after = metrics('etw-r46g-capture.metrics', (49940, 4, 13, 12))
assert after['irqs'] - before['irqs'] == 2
assert after['bytes'] - before['bytes'] == 11  # echo10 plus accepted Ctrl-U1
etw_native = decode('etw-r46g-capture.native')
assert 'len=10 data=65 63 68 6f 20 52 34 36 47 0a s1_after=06060606 via=irq' in etw_native
assert '\r\nR46G\r\n~ # ' in etw_native
etw_events = (BASE / 'etw-r46g-capture.metrics.events.txt').read_text()
assert 'sent=2 receipt=True' in etw_events
manifest = json.loads((BASE / 'etw-r46g-capture.manifest.json').read_text(encoding='utf-8-sig'))
assert manifest['completed'] is True and manifest['trace_stopped'] is True
trace = json.loads((BASE / 'etw-eud-summary.json').read_text())
assert trace['vid'] == '05c6' and trace['pid'] == '9505'
assert trace['events_lost'] == trace['buffers_lost'] == 0
assert [r['length'] for r in trace['out_transfers']] == [12, 3, 3]
assert all(r['usbd_status'] == r['ntstatus'] == '0x0' for r in trace['out_transfers'])
assert trace['payload_bytes_verified_by_etw'] is False
import xml.etree.ElementTree as ET
ns = {'e': 'http://schemas.microsoft.com/win/2004/08/events/event'}
selected = ET.parse(BASE/'etw-eud-selected.xml').getroot().findall('e:Event', ns)
assert len(selected) == 10
for ev in selected[4:]:
    f = {n.get('Name'): (n.text or '').strip() for n in ev.findall('.//e:Data', ns)}
    assert f['fid_UsbDevice'] == trace['device_handle']
    assert f['fid_PipeHandle'] == trace['out_pipe']
print('ETW: target OUT completions 12/3/3 are status zero; only echo plus one Ctrl-U adds IRQ frames. Payload bytes unverified.')
print('PASS: real IRQ capture and outputs/F1 verified; failed Windows C adds no IRQ; final B diagnostic live.')
print('Native stability is not fixed; original ETW payload bytes and physical USB behaviour remain unverified.')
