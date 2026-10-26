#!/usr/bin/env python3
"""Strict RX51 timing/accounting and direct cross-owner TX journal comparison."""
import argparse
import base64
from hashlib import sha256
import json
from pathlib import Path
import re
import struct
import zlib


def capture(root, name):
    raw = (root / (name + '.raw')).read_bytes()
    frames, text, pos = [], bytearray(), 0
    while pos < len(raw):
        assert pos + 2 <= len(raw) and raw[pos] == 0x90, ('framing', name, pos)
        n = raw[pos + 1]
        assert 1 <= n <= 4 and pos + n + 2 <= len(raw), ('length', name, pos)
        frames.append(raw[pos:pos + n + 2])
        text.extend(raw[pos + 2:pos + n + 2])
        pos += n + 2
    rows = [json.loads(s) for s in (root / (name + '.rx-audit.jsonl')).read_text(encoding='utf-8-sig').splitlines()]
    assert rows[0]['event'] == 'opened' and rows[-1]['event'] == 'closed'
    closed = rows[-1]
    reads = [r for r in rows if r['event'] == 'read']
    offset = 0
    for row in reads:
        assert row['raw_offset'] == offset and 0 < row['returned'] <= row['requested'] == row['in_queue']
        offset += row['returned']
    assert offset == len(raw) == closed['audit']['bytes']
    assert len(reads) == closed['audit']['reads'] and len(frames) == closed['received_frames']
    assert not closed['serial_is_open'] and closed['probe_detached']
    assert not closed['stray'] and not closed['buffered_bytes'] and not closed['queued_input']
    errors = [r for r in rows if r['event'] in ('error_sample', 'error_event')]
    assert not errors and not closed['audit']['error_mask']
    for field in ('in_queue', 'read_ms', 'decode_display_ms'):
        assert max(r[field] for r in reads) == closed['audit']['max_' + field]
    event_text = (root / (name + '.events.txt')).read_text(encoding='utf-8-sig')
    writes = [dict(ms=int(m[1]), n=int(m[2]), data=bytes.fromhex(m[3]), attempt=int(m[4]), sync=m[5] == 'True')
              for m in re.finditer(r'(?m)^(\d+) TX native len=(\d+) data=([0-9a-f ]+) attempt=(\d+) sync=(True|False)', event_text)]
    acks = [(int(m[1]), int(m[2]), bytes.fromhex(m[3])) for m in
            re.finditer(r'(?m)^(\d+) ACK native len=(\d+) data=([0-9a-f ]+)', event_text)]
    assert all(w['n'] == len(w['data']) and w['n'] in (1, *range(3, 15)) for w in writes)
    assert all(w['attempt'] == 1 for w in writes if not w['sync'])
    payload = text.decode('ascii')
    # Read logs have decoded text with CRLF; preserve framing/raw independently.
    assert (root / (name + '.txt')).read_bytes().decode('utf-8-sig').replace('\r\n', '\n') == payload.replace('\r\n', '\n')
    return dict(raw=raw, frames=frames, text=payload, rows=rows, writes=writes, acks=acks, closed=closed,
                summary=dict(bytes=len(raw), frames=len(frames), sha256=sha256(raw).hexdigest(), reads=len(reads),
                             audit=closed['audit'], pending_input=closed['pending_input'],
                             native_frames=closed['native_frames'], retries=closed['retries'], serial_closed=True))


def stats(line):
    registers = {'status', 'id', 'after', 'bad_id'}
    return {k: v if k in registers else int(v)
            for k, v in re.findall(r'([a-z][a-z0-9_]+)=([0-9a-f]+)(?: |$)', line)}


def analyze(root):
    a, b = capture(root, 'console-overlap-01'), capture(root, 'post-fault-01')
    assert a['closed']['pending_input'] and not b['closed']['pending_input']
    assert a['closed']['retries'] == 0 and b['closed']['retries'] == 1
    assert [(w['n'], w['data']) for w in a['writes'][:-1]] == [(n, d) for _, n, d in a['acks']]
    probe = a['writes'][-1]
    assert probe['data'] == b'R51H=1\n' and probe['n'] == 7 and probe['attempt'] == 1 and not probe['sync']
    commands = b'P=/sys/bus/platform/devices/88e0000.serial;cat $P/rx_stats $P/irq_watch\nprintf \'<6>R51LOCK:%0990d:R51END\\n\' 0 >/dev/kmsg\n'
    assert a['writes'][0]['data'] == b'\x15' and a['writes'][0]['sync']
    assert b''.join(w['data'] for w in a['writes'][1:-1]) == commands
    assert len(a['acks']) == a['closed']['native_frames'] + 1
    sync = [w for w in b['writes'] if w['sync']]
    assert [(w['data'], w['attempt']) for w in sync] == [(b'\x15', 1), (b'\x15', 2)]
    assert [(w['n'], w['data']) for w in b['writes'][1:]] == [(n, d) for _, n, d in b['acks']]
    recovery = b'dd if=$P/tx_journal of=/tmp/R51J1 bs=4096 count=1\nbase64 /tmp/R51J1\ncat $P/rx_stats $P/irq_watch;printf \'R51H=%s\\n\' "$R51H"\n'
    assert b''.join(w['data'] for w in b['writes'] if not w['sync']) == recovery
    assert len(b['acks']) == b['closed']['native_frames'] + 1
    marker, = [r for r in a['rows'] if r['event'] == 'overlap_marker']
    end, = [r for r in a['rows'] if r['event'] == 'overlap_end']
    assert marker['ms'] < probe['ms'] < end['ms'] < a['closed']['ms']
    assert a['closed']['ms'] - probe['ms'] >= 4000
    line, = re.findall(r'(?m)^\[\s*\d+\.\d+\]\s*R51LOCK:(0+):R51END\r?$', a['text'])
    assert len(line) == 990
    pre, = re.findall(r'polls=\d+ pending=\d+ bad=\d+ frames=\d+ f1=\d+.*?queued=\d+', a['text'])
    start, = re.findall(r'eud: tty byte=15 (polls=.*?active=\d+)', b['text'])
    post, = re.findall(r'polls=\d+ pending=\d+ bad=\d+ frames=\d+ f1=\d+.*?queued=\d+', b['text'])
    p, s, q = map(stats, (pre, start, post))
    assert p['frames'] == p['irqs'] == 48 and p['bytes'] == p['tty'] == 409
    assert s['frames'] == 53 and s['irqs'] == 54 and s['bytes'] == 459 and s['tty_before'] == 458
    # Four log-command frames and one accepted startup byte account for every
    # added accepted frame/byte. The seven-byte probe is absent from totals.
    assert s['frames'] - p['frames'] == 4 + 1 and s['bytes'] - p['bytes'] == 49 + 1
    assert s['irq_frames'] == 53 and s['poll_frames'] == 0 and s['empty'] == 1
    assert q['frames'] == q['irq_frames'] == 63 and q['bytes'] == q['tty'] == 583
    for row in (p, s, q):
        assert not any(row[k] for k in ('bad', 'no_tty', 'overrun', 'watchdog', 'drops', 'fault'))
        assert row['active'] == 1
    assert p['f1'] == q['f1'] == 0
    assert '\nR51H=\r\n' in b['text']
    assert 'waits=0 recovered=0 cleared=0 waiting=0 max_ms=0 first=00 last=00 err=0' in a['text'] and 'waits=0 recovered=0 cleared=0 waiting=0 max_ms=0 first=00 last=00 err=0' in b['text']

    # Recover the only immutable journal from the actual received base64.
    match, = re.finditer(rb'(?m)^RVVEVFhKNDg[A-Za-z0-9+/=]*\r?\n(?:[A-Za-z0-9+/=]+\r?\n)*', b['text'].encode())
    blob = base64.b64decode(re.sub(rb'\s+', b'', match.group()), validate=True)
    magic, version, size, count, recsize, first, last, crc, reserved = struct.unpack_from('<8sIIIIQQII', blob)
    assert (magic, version, size, count, recsize, reserved) == (b'EUDTXJ48', 1, 3120, 512, 6, 0)
    assert len(blob) == size and last - first + 1 == count
    check = bytearray(blob); check[40:44] = b'\0' * 4
    assert zlib.crc32(check) == crc
    if (root / 'tx-journal.bin').exists():
        assert (root / 'tx-journal.bin').read_bytes() == blob
    records = [blob[48 + i*6:54 + i*6] for i in range(count)]
    expected = []
    for record in records:
        n, source = record[:2]
        assert 1 <= n <= 4 and source in (1, 2) and not any(record[n+2:])
        expected.append(bytes([0x90, n]) + record[2:n+2])
    # A unique 16-frame recovery prefix anchors the boundary. Every frame on
    # both sides is then compared directly, without edit-distance alignment.
    candidates = [j for j in range(count-15) if expected[j:j+16] == b['frames'][:16]]
    j, = candidates
    assert j == 337 and expected[:j-1] == a['frames'][-(j-1):]
    assert expected[j:] == b['frames'][:count-j]
    assert records[j-1] == b'\x04\x02[ 58'
    assert b['text'].startswith('63.839589] eud: tty byte=15 ')
    result = dict(failure=a['summary'], recovery=b['summary'], console_zero_digits=990,
                  kmsg_write_bytes=1009, probe_bytes=7, probe_submissions=1,
                  marker_ms=marker['ms'], probe_ms=probe['ms'], end_ms=end['ms'],
                  observed_marker_to_end_ms=end['ms']-marker['ms'],
                  accepted_before=p, first_recovery_receipt=s, accepted_after=q,
                  probe_absent_from_accepted_counts=True, shell_variable_empty=True,
                  journal=dict(bytes=size, count=count, first_seq=first, last_seq=last, crc=f'{crc:08x}',
                               sha256=sha256(blob).hexdigest(), failed_owner_suffix_frames=j-1,
                               recovery_owner_prefix_frames=count-j,
                               missing_seq=first+j-1, missing_source=2,
                               missing_wire=expected[j-1].hex(' '), missing_text='[ 58',
                               direct_matched_frames=count-1),
                  limits='Host-observed output overlap and successful SerialPort.Write do not prove physical OUT arrival or lock latency. '
                         'One empty IRQ and first reopened sync failure cannot be assigned to the probe versus reopen. '
                         'The journal proves one issued console frame absent from Windows raw, not which hardware/USB/driver stage lost it. '
                         'No observed serial errors do not rule out unreported loss. IRQ grace still unexercised. No fix claimed.')
    return result, blob


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    result, blob = analyze(args.root)
    if args.out:
        args.out.write_text(json.dumps(result, indent=2) + '\n')
        (args.out.parent / 'tx-journal.bin').write_bytes(blob)
    print(json.dumps(result, indent=2))
