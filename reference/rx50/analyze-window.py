#!/usr/bin/env python3
"""Independent strict raw/read/journal accounting for the RX50 Windows sample."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import struct
import zlib


def analyze(root):
    raw = (root / 'windows-audit.raw').read_bytes()
    frames, payload, ends, pos = [], bytearray(), [], 0
    while pos < len(raw):
        assert pos + 2 <= len(raw) and raw[pos] == 0x90, ('framing', pos)
        n = raw[pos + 1]
        assert 1 <= n <= 4 and pos + 2 + n <= len(raw), ('length', pos, n)
        frames.append(raw[pos:pos + 2 + n])
        payload.extend(raw[pos + 2:pos + 2 + n])
        ends.append(len(payload))
        pos += 2 + n
    text = payload.decode('ascii')
    audit = [json.loads(line) for line in (root / 'windows-audit.rx-audit.jsonl').read_text(encoding='utf-8-sig').splitlines()]
    assert audit[0]['event'] == 'opened' and audit[-1]['event'] == 'closed'
    opened, closed = audit[0], audit[-1]
    reads = [row for row in audit if row['event'] == 'read']
    offset = 0
    for row in reads:
        assert row['raw_offset'] == offset and 0 < row['returned'] <= row['requested'] == row['in_queue']
        offset += row['returned']
    assert offset == len(raw) == closed['audit']['bytes']
    assert len(reads) == closed['audit']['reads']
    assert closed['received_frames'] == len(frames)
    assert not closed['serial_is_open'] and closed['probe_detached']
    assert not closed['stray'] and not closed['buffered_bytes'] and not closed['queued_input'] and not closed['pending_input']
    error_rows = [r for r in audit if r['event'] in ('error_sample', 'error_event')]
    assert not error_rows and not closed['audit']['error_mask']
    assert max(r['in_queue'] for r in reads) == closed['audit']['max_in_queue']
    assert max(r['read_ms'] for r in reads) == closed['audit']['max_read_ms']
    assert max(r['decode_display_ms'] for r in reads) == closed['audit']['max_decode_display_ms']
    event_text = (root / 'windows-audit.events.txt').read_text()
    writes = [(int(m[1]), bytes.fromhex(m[2]), int(m[3]), m[4] == 'True') for m in
              re.finditer(r'TX native len=(\d+) data=([0-9a-f ]+) attempt=(\d+) sync=(True|False)', event_text)]
    acks = [(int(m[1]), bytes.fromhex(m[2])) for m in
            re.finditer(r'ACK native len=(\d+) data=([0-9a-f ]+)', event_text)]
    assert [(n, data) for n, data, attempt, sync in writes] == acks
    assert all(n == len(data) and n in (1, *range(3, 15)) and attempt == 1 for n, data, attempt, sync in writes)
    assert writes[0] == (1, b'\x15', 1, True) and not any(sync for n, data, attempt, sync in writes[1:])
    commands = b'cat $P/rx_stats\ndd if=$P/tx_journal of=/tmp/R50J1 bs=4096 count=1\nbase64 /tmp/R50J1\ncat $P/irq_watch\n'
    assert b''.join(data for n, data, attempt, sync in writes[1:]) == commands
    assert len(writes) - 1 == closed['native_frames'] and not closed['retries']
    status = re.search(r'polls=\d+ pending=32 bad=0 frames=32 f1=0 bytes=251 tty=251 .*?queued=0', text)
    assert status and 'irqs=32 irq_frames=32 poll_frames=0 empty=0 watchdog=0 drops=0 fault=0 active=1' in status.group()
    assert 'waits=0 recovered=0 cleared=0 waiting=0 max_ms=0 first=00 last=00 err=0' in text
    blob = (root / 'windows-journal-1.bin').read_bytes()
    magic, version, size, count, recsize, first, last, crc, reserved = struct.unpack_from('<8sIIIIQQII', blob)
    assert (magic, version, count, recsize, reserved) == (b'EUDTXJ48', 1, 512, 6, 0)
    assert size == len(blob) == 48 + count * recsize and last - first + 1 == count
    check = bytearray(blob)
    check[40:44] = b'\0' * 4
    assert zlib.crc32(check) == crc
    records = [blob[48 + i * 6:54 + i * 6] for i in range(count)]
    expected = []
    for record in records:
        n, source = record[:2]
        assert 1 <= n <= 4 and source in (1, 2) and not any(record[2 + n:])
        expected.append(bytes([0x90, n]) + record[2:2 + n])
    # The first 225 records preceded the owner; the remaining 287 match the
    # first capture frames exactly. No edit-distance matching for this claim.
    assert expected[225:] == frames[:287]
    journal_text = b''.join(frame[2:] for frame in frames[:287]).decode('ascii')
    assert status.group() in journal_text
    summary = dict(raw_bytes=len(raw), raw_frames=len(frames), raw_sha256=sha256(raw).hexdigest(),
                   raw_reads=len(reads), native_data_frames=len(writes) - 1,
                   native_data_bytes=len(commands), startup_submissions=1,
                   errors_observed=len(error_rows), max_in_queue=closed['audit']['max_in_queue'],
                   max_poll_gap_ms=closed['audit']['max_poll_gap_ms'],
                   max_read_ms=closed['audit']['max_read_ms'],
                   max_decode_display_ms=closed['audit']['max_decode_display_ms'],
                   serial_closed=True, journal_records=count, journal_first_seq=first,
                   journal_last_seq=last, journal_crc=f'{crc:08x}',
                   directly_matched_records=287, matched_first_seq=first + 225,
                   unobserved_journal_prefix_records=225, rx_stats_in_matched_window=True,
                   limits='No old fault reproduced. These software/raw observations do not prove physical USB ACKs, '
                          'absence of every possible driver loss, or long-term stability. The first 225 journal '
                          'records predate this capture and are excluded.')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=Path)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    result = analyze(args.root)
    if args.out:
        args.out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
