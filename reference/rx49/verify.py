#!/usr/bin/env python3
"""Verify IN/software evidence; not a claim of physical or long-term reliability."""
import base64
from hashlib import sha256
import json
from pathlib import Path
import re
import runpy
import struct
import zlib

BASE = Path(__file__).resolve().parent
for line in (BASE / 'SHA256SUMS').read_text().splitlines():
    want, name = line.split('  ', 1)
    assert sha256((BASE / name).read_bytes()).hexdigest() == want, name
for row in json.loads((BASE / 'exports.json').read_text()):
    got = sha256((BASE / row['name']).read_bytes()).hexdigest()
    assert got == row['exported_sha256'], row['name']
    if Path(row['name']).suffix in ('.raw', '.bin', '.usbmon', '.py'):
        assert row['byte_identical'] and got == row['original_sha256'], row['name']

def decode(name):
    data = (BASE / (name + '.raw')).read_bytes()
    frames, payload, ends = [], bytearray(), []
    pos = 0
    while pos < len(data):
        assert pos + 2 <= len(data) and data[pos] == 0x90, (name, pos)
        n = data[pos + 1]
        assert 1 <= n <= 4 and pos + n + 2 <= len(data), (name, pos, n)
        frames.append(data[pos:pos + n + 2])
        payload.extend(data[pos + 2:pos + n + 2])
        ends.append(len(payload))
        pos += n + 2
    print(f'{name}: {len(frames)} frames/{len(data)} bytes, no resync/incomplete bytes')
    return frames, bytes(payload), ends

CAPTURE = {p.stem: decode(p.stem) for p in sorted(BASE.glob('*.raw'))}
assert len(CAPTURE) == 4
TEXT = {name: value[1].decode('ascii') for name, value in CAPTURE.items()}
analyze = runpy.run_path(str(BASE / 'analyze-usbmon-in.py'))['analyze']
current = json.loads((BASE / 'current-in-audit.json').read_text())
for saved in current:
    name = Path(saved['prefix']).name
    got = analyze(BASE / name)
    assert {k: v for k, v in got.items() if k != 'prefix'} == {k: v for k, v in saved.items() if k != 'prefix'}
    assert got['full_in_stream_equals_raw'] and not got['incomplete_payloads']
assert current[0]['complete_in_bytes'] == 940
assert current[1]['complete_in_bytes'] == 11066
assert current[1]['complete_in_data_urbs'] == 1858
assert current[1]['in_statuses'] == {'-2': 4818, '0': 1857}
assert current[1]['nonzero_status_with_data'] == [{'line': 2562, 'status': -2, 'actual': 6}]
line = (BASE / 'libusb-journal-b.usbmon').read_text().splitlines()[2561]
assert line.endswith('C Bi:1:002:1 -2 6 = 90046769 633d')
assert b'\x90\x04gic=' in (BASE / 'libusb-journal-b.raw').read_bytes()
assert 'gic=80 err=0' in TEXT['libusb-journal-b']

historical = json.loads((BASE / 'historical-in-audit.json').read_text())
assert len(historical) == 7
for saved in historical:
    original = Path(saved['prefix'])
    prefix = BASE.parent / original.parent.name / original.name
    got = analyze(prefix)
    assert {k: v for k, v in got.items() if k != 'prefix'} == {k: v for k, v in saved.items() if k != 'prefix'}
    assert got['full_in_stream_equals_raw'] and not got['incomplete_payloads']
    assert not got['nonzero_status_with_data']
stty = next(r for r in historical if Path(r['prefix']).name == 'libusb-stty')
assert stty['raw_bytes'] == 0 and stty['in_statuses'] == {'-2': 673}

for name, expected, count, byte_count in [
    ('libusb-journal', b'P=/sys/bus/platform/devices/88e0000.serial\n', 4, 43),
    ('libusb-journal-b', b"echo $P\ncat $P/irq_state\nprintf 'R49IN-%03d\\n' $(seq 1 60)\n"
                         b'cat $P/rx_stats\ndd if=$P/tx_journal of=/tmp/R49J1 bs=4096 count=1\n'
                         b'base64 /tmp/R49J1\ncat $P/irq_watch\n', 17, 160),
]:
    events = [json.loads(line) for line in (BASE / (name + '.events.jsonl')).read_text().splitlines()]
    writes = [e for e in events if e['event'] == 'out_submit']
    acks = [e for e in events if e['event'] == 'receipt']
    transport = json.loads((BASE / (name + '.json')).read_text())
    out_payloads, out_completions = [], []
    for line in (BASE / (name + '.usbmon')).read_text().splitlines():
        f = line.split()
        if len(f) < 6:
            continue
        address = f[3].split(':')
        if len(address) != 4 or address[0] != 'Bo' or tuple(map(int, address[1:])) != (transport['bus'], transport['address'], 2):
            continue
        if f[2] == 'S':
            assert f[6] == '='
            wire = bytes.fromhex(''.join(f[7:]))
            assert len(wire) == int(f[5]) <= 16
            out_payloads.append(wire)
        elif f[2] == 'C':
            assert int(f[4]) == 0
            out_completions.append(int(f[5]))
    assert out_payloads == [bytes.fromhex(e['hex']) for e in writes]
    assert out_completions == [len(wire) for wire in out_payloads]
    sync = [e for e in writes if e['sync']]
    data = [e for e in writes if not e['sync']]
    assert len(sync) == 1 and sync[0]['hex'] == '90 01 15'
    assert len(writes) == len(acks) == count + 1 and all(e['attempt'] == 1 for e in writes)
    assert all(e['length'] in (1, *range(3, 15)) for e in writes)
    assert len(expected) == byte_count and b''.join(bytes.fromhex(e['payload_hex']) for e in data) == expected
    for w, a in zip(writes, acks):
        assert (w['length'], w['payload_hex'], w['sync']) == (a['length'], a['payload_hex'], a['sync'])
        assert a['ms'] >= w['ms']
    closed = events[-1]
    assert closed['event'] == 'closed' and closed['data_frames'] == closed['acked'] == count
    assert closed['data_bytes'] == byte_count and closed['stray'] == closed['pending'] == 0
    assert closed['worker_alive'] == closed['errors'] == []
    assert not any(e['event'] == 'receipt_timeout' for e in events)
    assert 'RX46 IRQ fallback' not in TEXT[name]
    print(f'{name}: {len(writes)} complete OUT payloads/status-zero completions match submissions and receipts')
assert len(CAPTURE['libusb-journal'][0]) == 160
assert len(CAPTURE['libusb-journal-b'][0]) == 1858
assert ''.join(f'R49IN-{i:03d}\r\n' for i in range(1, 61)) in TEXT['libusb-journal-b']
assert '/sys/bus/platform/devices/88e0000.serial\r\n~ # ' in TEXT['libusb-journal-b']
assert 'frames=18 f1=0 bytes=135 tty=135 no_tty=0 overrun=0' in TEXT['libusb-journal-b']
assert 'irqs=18 irq_frames=18 poll_frames=0 empty=0 watchdog=0 drops=0 fault=0 active=1 queued=0' in TEXT['libusb-journal-b']
assert 'waits=0 recovered=0 cleared=0 waiting=0 max_ms=0 first=00 last=00 err=0' in TEXT['libusb-journal-b']

# Validate the immutable snapshot and a direct contiguous window independently.
blob = (BASE / 'libusb-journal-check-1.bin').read_bytes()
header = struct.unpack_from('<8sIIIIQQII', blob)
assert header[:7] == (b'EUDTXJ48', 1, 3120, 512, 6, 7713, 8224)
assert len(blob) == 3120 and header[8] == 0
check = bytearray(blob)
check[40:44] = bytes(4)
assert zlib.crc32(check) == header[7] == 0xe05be687
expected = []
for off in range(48, len(blob), 6):
    r = blob[off:off + 6]
    n, source = r[:2]
    assert 1 <= n <= 4 and source in (1, 2) and not any(r[2 + n:])
    expected.append(bytes([0x90, n]) + r[2:2 + n])
frames, payload, ends = CAPTURE['libusb-journal-b']
match = re.search(rb'(?m)^RVVEVFhKNDg[A-Za-z0-9+/=]*\r?\n(?:[A-Za-z0-9+/=]+\r?\n)*', payload)
assert match and base64.b64decode(re.sub(rb'\s+', b'', match.group()), validate=True) == blob
cutoff = sum(end <= match.start() for end in ends)
starts = [i for i in range(cutoff - 511) if frames[i:i + 512] == expected]
assert len(starts) == 1
summary = json.loads((BASE / 'libusb-journal-check-1.json').read_text())
assert summary['validated'] and summary['matched_frames'] == 512 and summary['interior_issues'] == []
assert summary['raw_sha256'] == sha256((BASE / 'libusb-journal-b.raw').read_bytes()).hexdigest()
print(f'Journal CRC {header[7]:08x}: 512 contiguous frames match at raw frame {starts[0]}; all IN bytes also match')

for name, frames_count, byte_count, before in [('baseline-ctrl-u', 3, 15, 14),
                                             ('libusb-journal', 4, 16, 15),
                                             ('libusb-journal-b', 9, 60, 59),
                                             ('native-final-installed', 27, 221, 220)]:
    line = re.search(r'tty byte=15 ([^\r\n]+)', TEXT[name]).group(1)
    fields = {k: int(v) for k, v in re.findall(r'(\w+)=(\d+)', line)}
    assert fields['frames'] == fields['pending'] == fields['irqs'] == fields['irq_frames'] == frames_count
    assert fields['bytes'] == byte_count and fields['tty_before'] == before
    assert fields['active'] == 1
    assert all(fields[k] == 0 for k in ('bad', 'no_tty', 'overrun', 'bad_id', 'bad_len',
                                       'poll_frames', 'empty', 'watchdog', 'drops', 'fault'))
assert '\r\nR49END1\r\n~ # ' in TEXT['native-final-installed']
assert len(CAPTURE['native-final-installed'][0]) == 90
events = (BASE / 'native-final-installed.events.txt').read_text()
assert events.count('TX native ') == 2 and 'attempt=2' not in events
assert 'len=13 data=65 63 68 6f 20 52 34 39 45 4e 44 31 0a' in events

meta = json.loads((BASE / 'libusb-journal-b.json').read_text())
assert meta['helper_sha256'] == sha256((BASE / 'eud-usb-session.py').read_bytes()).hexdigest()
assert meta['helper_sha256'] == '69bb5700313ddcd736bdb642da4314015ef1ad0764277b5197d252e258cfa8b2'
assert meta['libusb_backend_sha256'] == '0c86fc30235ce1d762ae14721e19a5efcadd8eea7d94771d4767d9b099ffba60'
assert sha256((BASE / 'eud-usb-session-before-display-fix.py').read_bytes()).hexdigest() == '2fc26164294ff9d40a5615a5f3433bf44640b9aa5806ff5d7de0a9ee0cdf85a4'
state = json.loads((BASE / 'final-state.json').read_text())
assert state['serial_closed'] and not state['flash_this_round'] and not state['reboot_this_round']
assert state['image'] == 'logdump-rx48-tx-journal.img' and state['ports'] == ['COM14']
assert len(state['devices']) == 3 and all(d['Status'] == 'OK' for d in state['devices'])
assert any('05c6:9505' in line and 'Shared' in line and 'Attached' not in line for line in state['target_usbipd'])
driver_hash = sha256((BASE.parent / 'rx48/eud-journal-candidate.c').read_bytes()).hexdigest()
assert driver_hash == 'e25d7fe215cab2ff842bdc3aa3bdf644d8f1701ecd27ea694fe43f848f5f5066'
assert any(row['Path'].endswith('linux-port\\eud.c') and row['Hash'].lower() == driver_hash for row in state['hashes'])
print('RX49 evidence verified. Physical RX/TX root cause and long-term stability remain unproven.')
