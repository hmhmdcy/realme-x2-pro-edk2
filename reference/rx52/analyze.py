#!/usr/bin/env python3
"""RX52: exact OUT/IN/raw accounting, IRQ deltas, and duplicate-aware TX gaps."""
import argparse
import base64
import bisect
from collections import Counter
import gzip
from hashlib import sha256
import itertools
import json
from pathlib import Path
import re
import struct
import zlib


def stats(line):
    registers = {'status', 'id', 'after', 'bad_id'}
    return {k: v if k in registers else int(v) for k, v in
            re.findall(r'([a-z][a-z0-9_]+)=([0-9a-f]+)(?: |$)', line)}


def analyze(root, name):
    meta = json.loads((root / (name + '.json')).read_text(encoding='utf-8-sig'))
    raw = (root / (name + '.raw')).read_bytes()
    frames, payload, ends, pos = [], bytearray(), [], 0
    while pos < len(raw):
        assert pos + 2 <= len(raw) and raw[pos] == 0x90
        n = raw[pos + 1]
        assert 1 <= n <= 4 and pos + 2 + n <= len(raw)
        frames.append(raw[pos:pos + n + 2]); payload.extend(raw[pos + 2:pos + n + 2])
        ends.append(len(payload)); pos += n + 2
    text = payload.decode('ascii')
    assert (root / (name + '.txt')).read_bytes().decode('utf-8-sig').replace('\r\n', '\n') == text.replace('\r\n', '\n')
    events = [json.loads(s) for s in (root / (name + '.events.jsonl')).read_text(encoding='utf-8-sig').splitlines()]
    closed = events[-1]
    assert closed['event'] == 'closed' and not closed['worker_alive'] and not closed['errors']
    assert closed['frames'] == len(frames) and not closed['stray'] and not closed['pending']
    assert closed['steps'] == 7 and closed['data_frames'] == 22 and closed['acked'] == 21 and closed['data_bytes'] == 252
    assert closed['synchronized'] and closed['overlap_receipt'] is False
    if meta.get('continuous_in_separate_sink'):
        assert closed['sink_drained'] and closed['io_bytes'] == len(raw)
        assert closed['io_reads'] == len([e for e in events if e['event'] == 'in'])
    reads = [bytes.fromhex(e['hex']) for e in events if e['event'] == 'in']
    assert b''.join(reads) == raw
    writes = [e for e in events if e['event'] == 'out_submit']
    acks = [e for e in events if e['event'] == 'receipt']
    missing, = [e for e in events if e['event'] == 'receipt_timeout']
    assert missing['payload_hex'] == '52 35 31 48 3d 31 0a' and missing['length'] == 7 and not missing['sync']
    assert len(writes) == 24 and len(acks) == 23 and all(e['attempt'] == 1 for e in writes)
    assert all(e['length'] in (1, *range(3, 15)) for e in writes)
    probes = [e for e in writes if e['payload_hex'] == missing['payload_hex']]
    probe, = probes
    wanted_acks = [(e['length'], e['payload_hex'], e['sync']) for e in writes if e is not probe]
    assert wanted_acks == [(e['length'], e['payload_hex'], e['sync']) for e in acks]
    marker, = [e for e in events if e['event'] == 'overlap_marker']
    end, = [e for e in events if e['event'] == 'overlap_end']
    assert marker['ms'] < probe['ms'] < end['ms'] < missing['ms']
    assert missing['ms'] - probe['ms'] >= 4000
    sync = [e for e in writes if e['sync']]
    assert len(sync) == 2 and all(e['hex'] == '90 01 15' for e in sync)
    assert sync[0]['ms'] < marker['ms'] and sync[1]['ms'] > missing['ms']
    index = int(name[-2:])
    commands = ("P=/sys/bus/platform/devices/88e0000.serial;cat $P/rx_stats $P/irq_watch\n"
                "printf '<6>R51LOCK:%0990d:R51END\\n' 0 >/dev/kmsg\nR51H=1\n"
                f"dd if=$P/tx_journal of=/tmp/R52J{index} bs=4096 count=1\nbase64 /tmp/R52J{index}\n"
                "cat $P/rx_stats $P/irq_watch;printf 'R51H=%s\\n' \"$R51H\"\n").encode()
    assert b''.join(bytes.fromhex(e['payload_hex']) for e in writes if not e['sync']) == commands
    lines = re.findall(r'polls=\d+ pending=\d+ bad=\d+ frames=\d+ f1=\d+.*?queued=\d+', text)
    before, after = map(stats, lines)
    sync_lines = re.findall(r'eud: tty byte=15 (polls=.*?active=\d+)', text)
    startup, recovery = map(stats, sync_lines)
    assert recovery['frames'] - before['frames'] == 5 and recovery['bytes'] - before['bytes'] == 50
    assert recovery['tty_before'] == before['tty'] + 49
    assert recovery['irqs'] - before['irqs'] == 6 and recovery['empty'] - before['empty'] == 1
    for row in (startup, before, recovery, after):
        assert row['active'] == 1 and row['irq_frames'] == row['frames']
        assert not any(row[k] for k in ('bad', 'no_tty', 'overrun', 'poll_frames', 'watchdog', 'drops', 'fault'))
    assert '\nR51H=\r\n' in text
    assert text.count('waits=0 recovered=0 cleared=0 waiting=0 max_ms=0 first=00 last=00 err=0') == 2

    path = root / (name + '.usbmon')
    trace = path.read_bytes() if path.exists() else gzip.decompress((root / (name + '.usbmon.gz')).read_bytes())
    target = (int(meta['bus']), int(meta['address']))
    in_data, out_data, out_done, in_times, submit_times = [], [], [], [], []
    statuses = Counter(); controls = []; pending_out = {}; out_rows = []
    for number, line in enumerate(trace.decode('ascii').splitlines(), 1):
        f = line.split(); assert len(f) >= 4
        address = f[3].split(':')
        assert len(address) == 4 and tuple(map(int, address[1:3])) == target
        direction, endpoint = address[0], int(address[3])
        if direction in ('Ci', 'Co'):
            controls.append(line); continue
        assert direction in ('Bi', 'Bo') and endpoint == (1 if direction == 'Bi' else 2)
        assert len(f) >= 6
        t, status, n = int(f[1]), int(f[4]), int(f[5])
        data = bytes.fromhex(''.join(f[7:])) if len(f) > 6 and f[6] == '=' else b''
        if direction == 'Bi':
            if f[2] == 'S': submit_times.append(t)
            if f[2] == 'C':
                statuses[str(status)] += 1
                if n:
                    assert len(data) == n <= 16
                    in_data.append(data); in_times.append(t)
        else:
            if f[2] == 'S':
                assert len(data) == n <= 16 and f[0] not in pending_out
                pending_out[f[0]] = (t, data)
                out_data.append(data)
            elif f[2] == 'C':
                sent_at, sent = pending_out.pop(f[0])
                assert status == 0 and n == len(sent)
                out_done.append(n); out_rows.append(dict(submitted_us=sent_at, completed_us=t, wire=sent.hex(' ')))
    assert not pending_out and not controls
    assert b''.join(in_data) == raw and in_data == reads
    assert out_data == [bytes.fromhex(e['hex']) for e in writes]
    assert out_done == [len(d) for d in out_data]
    assert [e['length'] for e in events if e['event'] == 'out_complete'] == out_done
    # Every positive IN is exactly one whole EUD frame in these captures.
    assert in_data == frames
    message, = re.finditer(rb'(?m)^\[\s*\d+\.\d+\]\s*R51LOCK:(0+):R51END\n', payload)
    digits = len(message[1])
    body_indices = [i for i, stop in enumerate(ends) if message.start() < stop and (ends[i-1] if i else 0) < message.end()]
    gaps = []
    for i in body_indices:
        j = bisect.bisect_left(submit_times, in_times[i])
        assert j < len(submit_times)
        gaps.append(dict(us=submit_times[j]-in_times[i], raw_frame=i, us_from_body_first=in_times[i]-in_times[body_indices[0]]))
    gap = max(gaps, key=lambda g: g['us'])
    export, = re.finditer(rb'(?m)^RVVEVFhKNDg[A-Za-z0-9+/=]*\r?\n(?:[A-Za-z0-9+/=]+\r?\n)*', payload)
    blob = base64.b64decode(re.sub(rb'\s+', b'', export.group()), validate=True)
    magic, version, size, count, recsize, first, last, crc, reserved = struct.unpack_from('<8sIIIIQQII', blob)
    assert (magic, version, size, count, recsize, reserved) == (b'EUDTXJ48', 1, 3120, 512, 6, 0)
    assert size == len(blob) and last-first+1 == count
    check = bytearray(blob); check[40:44] = bytes(4); assert zlib.crc32(check) == crc
    records = [blob[48+i*6:54+i*6] for i in range(count)]
    expected = []
    for r in records:
        n, source = r[:2]
        assert 1 <= n <= 4 and source in (1, 2) and not any(r[2+n:])
        expected.append(bytes([0x90, n]) + r[2:2+n])
    cutoff = sum(stop <= export.start() for stop in ends)
    starts = [i for i in range(cutoff-15) if frames[i:i+16] == expected[:16]]
    tails = [i for i in range(cutoff-15) if frames[i:i+16] == expected[-16:]]
    start, = starts; tail, = tails
    observed = frames[start:tail+16]
    collapse = lambda items: [(wire, len(list(group))) for wire, group in itertools.groupby(items)]
    want, got = collapse(expected), collapse(observed)
    assert [w for w, n in want] == [w for w, n in got]
    deficit = [(wire, a-b) for (wire, a), (_, b) in zip(want, got) if a != b]
    if meta.get('continuous_in_separate_sink'):
        assert not deficit and observed == expected and digits == 990
    else:
        assert deficit == [(bytes.fromhex('900430303030'), 2)] and digits == 982
        zero_indices = [i for i, r in enumerate(records) if expected[i] == deficit[0][0]]
        assert all(records[i][1] == 2 for i in zero_indices)
    zero_loss = 990-digits
    result = dict(name=name, helper_sha256=meta['helper_sha256'], pipelined=bool(meta.get('continuous_in_separate_sink')),
                  raw_bytes=len(raw), raw_frames=len(frames), raw_sha256=sha256(raw).hexdigest(),
                  usbmon_sha256=sha256(trace).hexdigest(), complete_in_completions=len(in_data),
                  in_statuses=dict(statuses), full_in_equals_raw=True, out_submissions=len(out_data),
                  out_completions_all_zero=True, no_control_transfers_in_capture=True,
                  probe_submissions=1, probe_receipt=False, marker_ms=marker['ms'], probe_ms=probe['ms'], end_ms=end['ms'],
                  probe_out_urb=next(r for r in out_rows if r['wire'] == probe['hex']),
                  accepted_before=before, recovery_receipt=recovery, accepted_after=after,
                  added_empty_irq=1, probe_absent_from_rx_tty=True, shell_variable_empty=True,
                  console_zero_digits=digits, console_missing_bytes=zero_loss, max_body_in_requeue_gap=gap,
                  journal=dict(first_seq=first, last_seq=last, crc=f'{crc:08x}', sha256=sha256(blob).hexdigest(),
                               expected_frames=count, observed_frames=len(observed), raw_start_frame=start,
                               missing_duplicate_zero_frames=count-len(observed), direct_or_run_count_comparison=True,
                               gap_position_ambiguous=bool(deficit)), closed=closed,
                  limits='Virtual HCD completion is not a physical USB ACK. Empty IRQ timing before the UART lock is unmeasured. '
                         'Two identical zero frames in serial mode cannot be assigned exact sequence numbers. '
                         'One pipeline contrast supports a host requeue effect, not a universal TX cause/fix. RX still fails in both modes.')
    return result, blob


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    results = []
    for name in ('usb-overlap-01', 'usb-overlap-02'):
        result, blob = analyze(args.root, name)
        results.append(result)
        if args.out: (args.out.parent / (name + '-journal.bin')).write_bytes(blob)
    if args.out: args.out.write_text(json.dumps(results, indent=2)+'\n')
    print(json.dumps([dict(name=r['name'], raw_bytes=r['raw_bytes'], console_digits=r['console_zero_digits'],
                           matched_journal_frames=r['journal']['observed_frames'], rx_probe_receipt=r['probe_receipt'],
                           max_body_requeue_gap_us=r['max_body_in_requeue_gap']['us']) for r in results]))
