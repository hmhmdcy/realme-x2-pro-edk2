#!/usr/bin/env python3
"""Verify observed RX47 outcomes, including remaining failures, not losslessness."""
from hashlib import sha256
from pathlib import Path
import json
import re

BASE = Path(__file__).resolve().parent
for line in (BASE / 'SHA256SUMS').read_text().splitlines():
    expected, name = line.split('  ', 1)
    assert sha256((BASE / name).read_bytes()).hexdigest() == expected, name
for row in json.loads((BASE / 'exports.json').read_text()):
    assert sha256((BASE / row['name']).read_bytes()).hexdigest() == row['exported_sha256']
    if row['name'].endswith('.raw'):
        assert row['byte_identical'] and row['original_sha256'] == row['exported_sha256']

def decode(name):
    raw = (BASE / f'{name}.raw').read_bytes()
    pos = frames = 0
    data = bytearray()
    while pos < len(raw):
        assert pos + 2 <= len(raw) and raw[pos] == 0x90, (name, pos)
        n = raw[pos + 1]
        assert 1 <= n <= 64 and pos + n + 2 <= len(raw), (name, pos, n)
        data.extend(raw[pos + 2:pos + n + 2])
        pos += n + 2
        frames += 1
    print(f'{name}: frames={frames}, bytes={len(raw)}, no resync/incomplete bytes')
    return data.decode('utf-8', errors='replace')

TEXT = {p.stem: decode(p.stem) for p in sorted(BASE.glob('*.raw'))}
assert len(TEXT) == 21

def metrics(name):
    line = re.search(r'eud: tty byte=15 (.+)', TEXT[name]).group(1)
    m = {key: int(value) for key, value in re.findall(r'(\w+)=(\d+)', line)}
    assert m['frames'] == m['pending'] == m['irqs'] == m['irq_frames']
    assert m['bytes'] == m['tty_before'] + 1
    for key in ('bad', 'no_tty', 'overrun', 'bad_len', 'poll_frames', 'empty',
                'watchdog', 'drops', 'fault'):
        assert m[key] == 0, (name, key, m[key])
    assert m['active'] == 1 and m['bad_id'] == 0
    return m

a = metrics('open-once.01-ctrl-u')
b = metrics('open-once.05-ctrl-u')
c = metrics('open-after-d.02-ctrl-u')
d = metrics('open-after-d.04-ctrl-u')
assert (a['frames'], a['bytes']) == (5, 14)
assert (b['frames'], b['bytes']) == (9, 53)
assert (c['frames'] - b['frames'], c['bytes'] - b['bytes']) == (1, 1)
assert (d['frames'], d['bytes']) == (12, 58)
for name in ('reopen-native-d', 'open-after-d.01-ctrl-u'):
    assert TEXT[name] == ''
    assert 'sent=1 receipt=False frames=0 stray=0 pending=0' in (BASE / f'{name}.events.txt').read_text()

for name, word in [('open-once.02-native-a', 'R47A1234'),
                   ('open-once.03-native-b', 'R47B1234'),
                   ('open-once.04-native-c', 'R47C')]:
    payload = ('echo ' + word + '\n').encode()
    assert f'len={len(payload)} data={payload.hex(" ")} s1_after=06060606 via=irq' in TEXT[name]
    assert re.search(r'\r?\n' + word + r'\r?\n~ # ', TEXT[name])
    assert 'sent=1 receipt=True' in (BASE / f'{name}.events.txt').read_text()
assert 'len=3 data=69 64 0a s1_after=06060606 via=irq' in TEXT['open-after-d.03-native-id']
assert 'uid=0 gid=0' in TEXT['open-after-d.03-native-id']

cases = {
    'native-host-tail': (b'echo R47HOST123\n', [14, 1, 1], 'R47HOST123'),
    'native-host-single-14': (b'echo R47HOST1\n', [14], 'R47HOST1'),
    'native-host-multiframe': (b'echo R47NATIVE-MULTIFRAME-OUTPUT-1234\n', [14, 14, 10],
                              'R47NATIVE-MULTIFRAME-OUTPUT-1234'),
    'native-interactive': (b'echo R47PASTE1\nunfinished\x15id\n', [14, 1, 10, 4], 'uid=0 gid=0'),
    'native-after-reboot': (b"echo R47BOOT1\nprintf 'R47TX-%03d\\n' $(seq 1 20)\n"
                            b'R47V=retained\necho $R47V\n' +
                            b'cat /sys/bus/platform/devices/88e0000.serial/rx_stats\n' * 2,
                            [14, 14, 14, 6, 14, 11, 14, 14, 14, 12, 14, 14, 14, 12], 'retained'),
    'native-final-installed': (b'echo R47END1\n', [13], 'R47END1'),
}
for name, (payload, lengths, output) in cases.items():
    events = (BASE / f'{name}.events.txt').read_text()
    writes = re.findall(r'(\d+) TX native len=(\d+) data=([0-9a-f ]+) attempt=(\d+) sync=(True|False)', events)
    acks = re.findall(r'(\d+) ACK native len=(\d+) data=([0-9a-f ]+)', events)
    data = [w for w in writes if w[4] == 'False']
    sync = [w for w in writes if w[4] == 'True']
    assert sync and all(w[1:3] == ('1', '15') for w in sync)
    assert events.count('SYNC fresh Ctrl-U receipt') == 1
    assert len(sync) == (2 if name == 'native-host-single-14' else 1)
    assert [int(w[1]) for w in data] == lengths, name
    assert all(w[3] == '1' and int(w[1]) in (1, *range(3, 15)) for w in data)
    assert b''.join(bytes.fromhex(w[2]) for w in data) == payload, name
    assert len(acks) == len(data) + 1
    for w, ack in zip(data, acks[1:]):
        assert w[1:3] == ack[1:3] and int(ack[0]) >= int(w[0])
        chunk = bytes.fromhex(w[2])
        receipt = ('eud: tty byte=' + chunk.hex()) if len(chunk) == 1 else (
            f'eud: rx frame len={len(chunk)} data={chunk.hex(" ")}')
        assert receipt in TEXT[name], (name, receipt)
    assert output in TEXT[name] and '~ # ' in TEXT[name]
    metrics(name)

legacy = (BASE / 'compatible-host-regression.events.txt').read_text()
writes = re.findall(r'TX byte=([0-9a-f]{2}) attempt=(\d+)', legacy)
assert bytes(int(w[0], 16) for w in writes) == b'\x15echo R47COMPAT\n'
assert all(w[1] == '1' for w in writes) and legacy.count(' ACK byte=') == 16
assert '\nR47COMPAT\r\n~ # ' in TEXT['compatible-host-regression']

after = TEXT['native-after-reboot']
numbered = re.findall(r'^R47TX-(\d{3})\r?$', after, re.M)
assert numbered == [f'{i:03d}' for i in range(1, 21)]
assert re.search(r'\r?\nretained\r?\n~ # ', after)
assert 'irqs=11 irq_frames=11 poempty=0 watchdog=0 drops=0 fault=0 active=1 queued=0' in after
assert 'RX46 IRQ fallback fault=4 irqs=14 irq_frames=14 watchdog=1 empty=0 drops=0' in after
assert 'len=12 data=61 6c 2f 72 78 5f 73 74 61 74 73 0a s1_after=06060606 via=poll' in after
assert 'pending=15 bad=0 frames=15 f1=0 bytes=182 tty=182 no_tty=0 overrun=0' in after
assert 'irqs=14 irq_frames=14 poll_frames=1 empty=0 watchdog=1 drops=0 fault=4 active=0 queued=0' in after
source = (BASE.parents[1] / 'linux-port/eud.c').read_text()
assert 'irq_frames=%u poll_frames=%u empty=%u' in source
assert len('ll_frames=0 ') == 12

for name, via, tries in [('f1', 'irq', 1), ('f1-after-fallback', 'poll', 5)]:
    assert f'RX46 F1 via={via}' in TEXT[name]
    assert 'reboot2 bootloader requested' in TEXT[name]
    assert f'sent={tries} receipt=True' in (BASE / f'{name}.events.txt').read_text()
for name in ('same-image-reboot', 'final-boot'):
    text = TEXT[name]
    for marker in ('AHB2PHY TOP_CFG=00000011 original=00000000',
                   'RX46 IRQ requested virq=19 hwirq=524 route=legacy-SPI492',
                   'RX46 IRQ armed virq=19 active=1 mask=01 original=1c',
                   '[tty] shell started on /dev/ttyEUD0'):
        assert marker in text
    assert 'RX46 IRQ fallback' not in text
    assert 'sent=0,0' in (BASE / f'{name}.events.txt').read_text()

ctl = json.loads((BASE / 'etw-eud-controls.json').read_text())
assert ctl['source_etl_sha256'] == 'b2911052876e89712276081e5ad0e6491f525bad8aed2f64076261dc3b37f595'
start = [e for e in ctl['control_events'] if e['id'] == 23]
done = [e for e in ctl['control_events'] if e['id'] == 24]
assert len(start) == len(done) == 4
assert [e['fields']['fid_URB_Setup_wIndex'] for e in start] == ['0x81', '0x2', '0x81', '0x2']
for a, b in zip(start, done):
    f, g = a['fields'], b['fields']
    assert f['fid_URB_Setup_bmRequestType'] == '0x2' and f['fid_URB_Setup_bRequest'] == '0x1'
    assert f['fid_URB_Setup_wValue'] == f['fid_URB_Setup_wLength'] == '0x0'
    assert f['fid_URB_Ptr'] == g['fid_URB_Ptr'] and f['fid_IRP_Ptr'] == g['fid_IRP_Ptr']
    assert g['fid_URB_Hdr_Status'] == g['fid_IRP_NtStatus'] == '0x0'
assert len([e for e in ctl['hub_reset_events'] if e['id'] == 92 and e['fields']['fid_UrbFunction'] == '0x1E']) == 4
assert not ctl['physical_data_pid_observed'] and not ctl['payload_bytes_verified']
state = json.loads((BASE / 'final-state.json').read_text())
assert state['serial_closed'] and state['flashes'] == state['new_elevated_captures'] == 0
assert len(state['pnp']) == 3 and all(d['Status'] == 'OK' for d in state['pnp'])
assert all('Attached' not in line for line in state['usbipd_eud_lines'])
assert state['fastboot_serial'] == '62bc28a1' and state['fastboot_product'] == 'msmnile'
assert sha256((BASE / 'eud-terminal-native.ps1').read_bytes()).hexdigest() == '9c7a16f1f389a0dbbf3436f1383221cdf6c00e348f25b6e3590a479dab103d57'
assert sha256((BASE / 'eud-terminal-before-rx47.ps1').read_bytes()).hexdigest() == 'f9bdc49e022ce4f9b1537e61ab8c5e7c2ea15a91c6447e15e64372aef8a6dc97'
print('RX47 verified: native operation/session boundary, actual TX loss and watchdog fallback; stability remains open.')
