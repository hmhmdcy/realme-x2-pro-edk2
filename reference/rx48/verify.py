#!/usr/bin/env python3
"""Verify RX48 measurements and CRC evidence, without asserting stability."""
from pathlib import Path
from hashlib import sha256
import base64
import json
import re
import struct
import zlib

BASE = Path(__file__).resolve().parent
for line in (BASE / 'SHA256SUMS').read_text().splitlines():
    want, name = line.split('  ', 1)
    assert sha256((BASE / name).read_bytes()).hexdigest() == want, name
for row in json.loads((BASE / 'exports.json').read_text()):
    got = sha256((BASE / row['name']).read_bytes()).hexdigest()
    assert got == row['exported_sha256'], row['name']
    if Path(row['name']).suffix in ('.raw', '.bin', '.c'):
        assert row['byte_identical'] and got == row['original_sha256']

def decode(name):
    raw = (BASE / (name + '.raw')).read_bytes()
    frames, payload, ends = [], bytearray(), []
    pos = 0
    while pos < len(raw):
        assert pos + 2 <= len(raw) and raw[pos] == 0x90, (name, pos)
        n = raw[pos + 1]
        assert 1 <= n <= 64 and pos + n + 2 <= len(raw), (name, pos, n)
        frames.append(raw[pos:pos + n + 2])
        payload.extend(raw[pos + 2:pos + n + 2])
        ends.append(len(payload))
        pos += n + 2
    print(f'{name}: {len(frames)} frames, {len(raw)} bytes, no resync/incomplete bytes')
    return frames, bytes(payload), ends

CAPTURE = {p.stem: decode(p.stem) for p in sorted(BASE.glob('*.raw'))}
assert len(CAPTURE) == 11
TEXT = {name: data[1].decode('utf-8', errors='replace') for name, data in CAPTURE.items()}
for name, count in [('watchdog-boot', 13923), ('journal-boot', 13935),
                    ('journal-final-boot', 13919)]:
    assert len(CAPTURE[name][0]) == count
    text = TEXT[name]
    assert 'AHB2PHY TOP_CFG=00000011 original=00000000' in text
    assert 'RX46 IRQ requested virq=19 hwirq=524 route=legacy-SPI492' in text
    assert 'RX46 IRQ armed virq=19 active=1 mask=01 original=1c grace_ms=100' in text
    assert '[tty] shell started on /dev/ttyEUD0' in text
    assert 'RX46 IRQ fallback' not in text
    assert f'finished frames={count} stray=0 pending=0 sent=0,0' in (BASE / (name + '.events.txt')).read_text()

long_path = b'/sys/bus/platform/devices/88e0000.serial'
cases = {
    'native-watchdog': (b'cat ' + long_path + b'/rx_stats\ncat ' + long_path +
                        b"/irq_watch\nprintf 'R48FLOW-%03d\\n' $(seq 1 30)\ncat " +
                        long_path + b'/rx_stats\ncat ' + long_path + b'/irq_watch\n',
                        19, 255, 908),
    'native-journal': (b'P=' + long_path + b"\nprintf 'R48BASE-%03d\\n' $(seq 1 30)\n"
                       b'cat $P/irq_state\ncat $P/rx_stats\n'
                       b'dd if=$P/tx_journal of=/tmp/R48J1 bs=4096 count=1\n'
                       b'base64 /tmp/R48J1\ncat $P/irq_watch\n', 20, 198, 1860),
    'native-final-installed': (b'echo R48END1\n', 1, 14, 87),
}
for name, (expected, count, byte_count, tx_frames) in cases.items():
    events = (BASE / (name + '.events.txt')).read_text()
    writes = re.findall(r'(\d+) TX native len=(\d+) data=([0-9a-f ]+) attempt=(\d+) sync=(True|False)', events)
    sync = [w for w in writes if w[4] == 'True']
    data = [w for w in writes if w[4] == 'False']
    assert len(sync) == 1 and sync[0][1:4] == ('1', '15', '1'), name
    assert events.count('SYNC fresh Ctrl-U receipt') == 1
    assert len(data) == count and len(expected) + 1 == byte_count, name
    assert b''.join(bytes.fromhex(w[2]) for w in data) == expected, name
    acks = re.findall(r'(\d+) ACK native len=(\d+) data=([0-9a-f ]+)', events)
    assert len(acks) == count + 1
    for w, a in zip(writes, acks):
        assert w[1:3] == a[1:3] and int(a[0]) >= int(w[0]), (name, w, a)
    for w in data:
        n = int(w[1])
        assert n in (1, *range(3, 15)) and w[3] == '1'
        payload = bytes.fromhex(w[2])
        assert len(payload) == n
        if n > 1:
            assert f'len={n} data={payload.hex(" ")} s1_after=06060606 via=irq' in TEXT[name]
        else:
            assert f'tty byte={payload[0]:02x}' in TEXT[name]
    assert len(CAPTURE[name][0]) == tx_frames
    assert 'RX46 IRQ fallback' not in TEXT[name]

for name, prefix in [('native-watchdog', 'R48FLOW'), ('native-journal', 'R48BASE')]:
    # A pasted the next query while printing: a complete receipt printk was
    # inserted between R48FLOW-018 and its newline. Preserve original bytes.
    numbered = re.findall(re.escape(prefix) + r'-(\d{3})', TEXT[name])
    assert numbered == [f'{i:03d}' for i in range(1, 31)], (name, numbered)
    if name == 'native-journal':
        assert ''.join(f'{prefix}-{i:03d}\r\n' for i in range(1, 31)) in TEXT[name]
    assert 'waits=0 recovered=0 cleared=0 waiting=0 max_ms=0 first=00 last=00 err=0' in TEXT[name]
assert 'gic=80 err=0' in TEXT['native-journal']
assert 'frames=13 f1=0 bytes=113 tty=113 no_tty=0 overrun=0' in TEXT['native-journal']
assert 'irqs=13 irq_frames=13 poll_frames=0 empty=0 watchdog=0 drops=0 fault=0 active=1 queued=0' in TEXT['native-journal']
assert 'frames=16 f1=0 bytes=200 tty=200' in TEXT['native-watchdog']
assert '\r\nR48END1\r\n~ # ' in TEXT['native-final-installed']

events = (BASE / 'compatible-journal.events.txt').read_text()
compat = re.findall(r'\d+ TX byte=([0-9a-f]{2}) attempt=(\d+)', events)
assert compat[:2] == [('15', '1'), ('15', '2')]
assert all(attempt == '1' for _, attempt in compat[2:])
assert bytes(int(value, 16) for value, _ in compat[2:]) == b'echo R48COMPAT\n'
assert len(re.findall(r'ACK byte=', events)) == 16
assert '\r\nR48COMPAT\r\n~ # ' in TEXT['compatible-journal']

for name in ('baseline-f1', 'watchdog-f1', 'journal-f1'):
    assert 'reboot2 bootloader requested' in TEXT[name]
    assert 'F1 via=irq' in TEXT[name]
    assert 'sent=2 receipt=True' in (BASE / (name + '.events.txt')).read_text()
for name in ('watchdog-fastboot-product.txt', 'journal-fastboot-product.txt'):
    text = (BASE / name).read_text()
    assert 'product: msmnile' in text
    # A's archived file contains getvar only; B also retained devices output.
    if name == 'journal-fastboot-product.txt':
        assert '62bc28a1' in text

# Independent direct frame-window comparison (no SequenceMatcher).
blob = (BASE / 'journal-first-1.bin').read_bytes()
magic, version, size, count, recsize, first, last, crc, reserved = struct.unpack_from('<8sIIIIQQII', blob)
assert (magic, version, size, count, recsize, first, last, reserved) == (
    b'EUDTXJ48', 1, 3120, 512, 6, 7415, 7926, 0)
assert len(blob) == 48 + count * recsize == size
check = bytearray(blob)
check[40:44] = bytes(4)
assert zlib.crc32(check) == crc == 0xa3e1b9b4
expected = []
for off in range(48, size, recsize):
    record = blob[off:off + recsize]
    n, source = record[:2]
    assert 1 <= n <= 4 and source in (1, 2) and not any(record[2 + n:])
    expected.append(bytes([0x90, n]) + record[2:2 + n])
frames, payload, ends = CAPTURE['native-journal']
match = re.search(rb'(?m)^RVVEVFhKNDg[A-Za-z0-9+/=]*\r?\n(?:[A-Za-z0-9+/=]+\r?\n)*', payload)
assert match
assert base64.b64decode(re.sub(rb'\s+', b'', match.group()), validate=True) == blob
cutoff = sum(end <= match.start() for end in ends)
starts = [i for i in range(cutoff - count + 1) if frames[i:i + count] == expected]
assert len(starts) == 1, starts
summary = json.loads((BASE / 'journal-first-1.json').read_text())
assert summary['validated'] and summary['matched_frames'] == 512 and summary['interior_issues'] == []
assert summary['raw_sha256'] == sha256((BASE / 'native-journal.raw').read_bytes()).hexdigest()
print(f'Journal: valid CRC {crc:08x}; seq {first}..{last}, all 512 frames match one raw window at frame {starts[0]}')

source_hashes = {
    'eud-before-rx48.c': '673c485843bc551788a0eb90499207371110807d4700a1f3f20d42b76e4e921f',
    'eud-watchdog-candidate.c': 'f76c670a2c5be73521154b666dc42574ee4690966953ca8fb18202de92faf1f6',
    'eud-journal-candidate.c': 'e25d7fe215cab2ff842bdc3aa3bdf644d8f1701ecd27ea694fe43f848f5f5066',
}
for name, want in source_hashes.items():
    assert sha256((BASE / name).read_bytes()).hexdigest() == want
assert sha256((BASE.parent.parent / 'linux-port/eud.c').read_bytes()).hexdigest() == source_hashes['eud-journal-candidate.c']
for name in ('build-watchdog.log', 'build-journal.log'):
    assert not re.search(r'warning:|error:', (BASE / name).read_text())
assert 'error:' in (BASE / 'build-journal-api-error.log').read_text()
state = json.loads((BASE / 'final-state.json').read_text())
assert state['serial_closed'] and state['image'] == 'logdump-rx48-tx-journal.img'
assert len(state['devices']) == 3 and all(d['Status'] == 'OK' for d in state['devices'])
assert state['ports'] == ['COM14']
print('RX48 evidence verified. Grace branches unexercised; historical RX/TX stability remains unresolved.')
