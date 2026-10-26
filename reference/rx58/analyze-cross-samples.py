"""Replay existing captures; no device IO and no guessed gap interpolation."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import struct
import zlib


def analyze(ref):
    deps = {}

    def read(rel):
        path = ref / rel
        raw = path.read_bytes()
        checksum = next(line.split('  ', 1)[0] for line in
                        (path.parent/'SHA256SUMS').read_text().splitlines()
                        if line.split('  ', 1)[1] == path.name)
        assert sha256(raw).hexdigest() == checksum, rel
        deps[rel] = checksum
        return raw

    def decode(rel):
        raw = read(rel)
        pos, frames = 0, []
        while pos < len(raw):
            assert raw[pos] == 0x90 and pos+2 <= len(raw), (rel, pos)
            n = raw[pos+1]
            assert 1 <= n <= 4 and pos+n+2 <= len(raw), (rel, pos, n)
            frames.append(raw[pos:pos+n+2])
            pos += n+2
        return raw, frames, b''.join(frame[2:] for frame in frames)

    def journal(rel):
        blob = read(rel)
        magic, version, size, count, recsize, first, last, crc, reserved = struct.unpack_from('<8sIIIIQQII', blob)
        assert (magic, version, size, count, recsize, reserved) == (b'EUDTXJ48', 1, 3120, 512, 6, 0)
        assert len(blob) == size and last-first+1 == count
        check = bytearray(blob)
        check[40:44] = bytes(4)
        assert zlib.crc32(check) == crc
        records = [blob[48+6*i:54+6*i] for i in range(count)]
        wanted = []
        for row in records:
            n, source = row[:2]
            assert 1 <= n <= 4 and source in (1, 2) and not any(row[2+n:])
            wanted.append(bytes([0x90, n])+row[2:2+n])
        return first, last, crc, records, wanted

    specs = [
        dict(session='RX51', journal='rx51/tx-journal.bin', before='rx51/console-overlap-01.raw',
             affected='rx51/post-fault-01.raw', events='rx51/post-fault-01.events.txt',
             audit='rx51/post-fault-01.rx-audit.jsonl', seq=11733, timestamp='5863.839589'),
        dict(session='RX53', journal='rx53/final-tx-journal.bin', before='rx53/candidate-final-boot.raw',
             affected='rx53/installed-final-native.raw', events='rx53/installed-final-native.events.txt',
             after='rx53/post-final-journal.raw', seq=7287, timestamp='95.409512'),
        dict(session='RX55', journal='rx55/windows-tx-journal.bin', before='rx54/restored-native.raw',
             affected='rx55/windows-perf-01.raw', events='rx55/windows-perf-01.events.txt',
             audit='rx55/windows-perf-01.rx-audit.jsonl', seq=7376, timestamp='1688.479011'),
    ]
    result = []
    for spec in specs:
        first, last, crc, records, wanted = journal(spec['journal'])
        raw, frames, body = decode(spec['affected'])
        _, before, _ = decode(spec['before'])
        # A unique contiguous 20-frame prefix fixes the location. Every other
        # record is then matched directly, without insertion/deletion search.
        matches = [i for i in range(len(wanted)-20)
                   if wanted[i+1:i+21] == frames[:20]]
        k, = matches
        assert k > 0 and first+k == spec['seq'] and records[k][1] == 2
        assert before[-k:] == wanted[:k]
        count = min(len(frames), len(wanted)-k-1)
        assert frames[:count] == wanted[k+1:k+1+count]
        after_count = 0
        if 'after' in spec:
            _, after, _ = decode(spec['after'])
            after_count = len(wanted)-k-1-count
            assert after[:after_count] == wanted[k+1+count:]
        assert k+count+after_count == 511
        assert len(wanted[k]) == 6
        first_line = body.split(b'\n', 1)[0].rstrip(b'\r')
        issued_line = wanted[k][2:]+first_line
        m = re.fullmatch(rb'\[\s*(\d+\.\d+)\] eud: tty byte=15 .*', issued_line)
        assert m and m[1].decode() == spec['timestamp']
        events = read(spec['events']).decode('utf-8-sig')
        sync = [dict(ms=int(ms), attempt=int(attempt)) for ms, attempt in
                re.findall(r'(?m)^(\d+) TX native len=1 data=15 attempt=(\d+) sync=True', events)]
        ack, = [int(ms) for ms in re.findall(r'(?m)^(\d+) ACK native len=1 data=15\r?$', events)]
        row = dict(session=spec['session'], journal_first=first, journal_last=last,
                   journal_crc=f'{crc:08x}', missing_seq=first+k, missing_wire=wanted[k].hex(' '),
                   source='console', missing_frame_is_affected_raw_start=True,
                   restored_first_line=issued_line.decode(), raw_first_wire=frames[0].hex(' '),
                   first_sync_attempts=sync, first_sync_ack_ms=ack,
                   direct_before=k, direct_affected=count, direct_after=after_count,
                   direct_matches=511, affected_bytes=len(raw), affected_frames=len(frames))
        if 'audit' in spec:
            audit = [json.loads(s) for s in read(spec['audit']).decode('utf-8-sig').splitlines()]
            assert audit[0]['event'] == 'opened' and audit[-1]['event'] == 'closed'
            assert not audit[-1]['serial_is_open']
            reads = [r for r in audit if r['event'] == 'read']
            assert reads[0]['raw_offset'] == 0
            row['opened_ms'] = audit[0]['ms']
            row['first_read_ms'] = reads[0]['ms']
            row['first_read_wire_bytes'] = reads[0]['returned']
            perf = [r for r in audit if r['event'] == 'perf']
            if perf:
                assert perf[0]['raw_position'] == 0 and perf[1]['raw_position'] == 309
                assert perf[1]['perf']['received']-perf[0]['perf']['received'] == 309
                row['first_status_raw_bytes'] = 309
                row['first_status_received_delta'] = 309
                row['first_status_cpu_issued_bytes'] = 315
        result.append(row)

    raw, frames, body = decode('rx57/windows-log-02.raw')
    first, last, crc, records, wanted = journal('rx57/windows-tx-journal.bin')
    starts = [i for i in range(len(wanted)-20) if wanted[i:i+20] == frames[:20]]
    k, = starts
    _, prior, _ = decode('rx55/windows-perf-01.raw')
    assert k == 55 and prior[-k:] == wanted[:k] and frames[:512-k] == wanted[k:]
    assert re.match(rb'\[\s*\d+\.\d+\] eud: tty byte=15 ', body)
    passing = dict(session='RX57', affected_bytes=len(raw), initial_status_prefix_present=True,
                   direct_matches=512, before_matches=k, current_matches=512-k,
                   journal_crc=f'{crc:08x}', limit='Passing contrast; logging can change timing.')
    return dict(gaps=result, passing=passing, dependencies=deps,
                conclusion='All three CRC-proven TX gaps are the first console timestamp frame of the first observed status in a reopened Windows owner. RX53 accepted its first Ctrl-U, so initial RX failure is not required for a TX gap.',
                limits=['This is a three-sample association, not a measured cause or failure rate.',
                        'CPU-issued journal records do not prove physical USB ACK or DATA0/1.',
                        'The other 511 records match directly; RX53 includes a later recovery owner.'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('reference', type=Path)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    result = analyze(args.reference)
    if args.out:
        args.out.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(gaps=[{k:r[k] for k in ('session', 'missing_seq', 'missing_wire', 'direct_matches', 'first_sync_attempts')} for r in result['gaps']], passing=result['passing']), indent=2))
