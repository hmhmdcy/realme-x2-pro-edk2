#!/usr/bin/env python3
"""Validate an immutable TX journal exported through base64, then compare raw frames."""
from pathlib import Path
import argparse
import base64
import difflib
import json
import re
import struct
import zlib

parser = argparse.ArgumentParser()
parser.add_argument('raw', type=Path)
parser.add_argument('--out', required=True, type=Path)
args = parser.parse_args()
raw = args.raw.read_bytes()
frames = []
payload = bytearray()
ends = []
pos = 0
while pos < len(raw):
    assert pos + 2 <= len(raw) and raw[pos] == 0x90, ('framing', pos)
    n = raw[pos + 1]
    assert 1 <= n <= 64 and pos + n + 2 <= len(raw), ('length', pos, n)
    frames.append(raw[pos:pos + n + 2])
    payload.extend(raw[pos + 2:pos + n + 2])
    ends.append(len(payload))
    pos += n + 2

exports = []
pattern = rb'(?m)^RVVEVFhKNDg[A-Za-z0-9+/=]*\r?\n(?:[A-Za-z0-9+/=]+\r?\n)*'
for match in re.finditer(pattern, payload):
    try:
        data = base64.b64decode(re.sub(rb'\s+', b'', match.group()), validate=True)
        magic, version, size, count, recsize, first, last, crc, reserved = struct.unpack_from('<8sIIIIQQII', data)
        assert magic == b'EUDTXJ48' and version == 1 and recsize == 6 and reserved == 0
        assert size == len(data) == 48 + count * recsize and 0 <= count <= 512
        check = bytearray(data)
        check[40:44] = b'\0' * 4
        assert zlib.crc32(check) == crc, ('CRC', hex(zlib.crc32(check)), hex(crc))
        assert first == (last - count + 1 if count else 0)
    except (AssertionError, ValueError, struct.error) as error:
        print(f'Invalid base64/journal at payload offset {match.start()}: {error}')
        continue
    records = [data[48 + i * recsize:48 + (i + 1) * recsize] for i in range(count)]
    expected = []
    for record in records:
        n, source = record[:2]
        assert 1 <= n <= 4 and source in (1, 2) and not any(record[2 + n:])
        expected.append(bytes([0x90, n]) + record[2:2 + n])
    # Only compare capture frames preceding this immutable file's base64 output.
    # Unknown leading/trailing journal records are excluded from loss claims.
    cutoff = sum(end <= match.start() for end in ends)
    observed = frames[:cutoff]
    matcher = difflib.SequenceMatcher(None, expected, observed, autojunk=False)
    blocks = [b for b in matcher.get_matching_blocks() if b.size]
    anchors = [b for b in blocks if b.size >= 8]
    assert anchors, 'No substantial anchor between issued records and capture'
    lo, hi = anchors[0].a, anchors[-1].a + anchors[-1].size
    issues = []
    for tag, a1, a2, b1, b2 in matcher.get_opcodes():
        if tag == 'equal' or a1 < lo or a2 > hi:
            continue
        if a1 == a2 and (a1 <= lo or a1 >= hi):
            continue
        issues.append(dict(kind=tag, first_seq=first + a1,
                           expected=[p.hex(' ') for p in expected[a1:a2]],
                           sources=[records[i][1] for i in range(a1, a2)],
                           received=[p.hex(' ') for p in observed[b1:b2]],
                           expected_text=b''.join(p[2:] for p in expected[a1:a2]).decode('ascii', errors='replace')))
    summary = dict(version=version, bytes=size, records=count, first_seq=first,
                   last_seq=last, crc=f'{crc:08x}', validated=True,
                   raw_sha256=__import__('hashlib').sha256(raw).hexdigest(),
                   base64_payload_offset=match.start(), capture_cutoff_frames=cutoff,
                   anchored_first_seq=first + lo, anchored_last_seq=first + hi - 1,
                   matched_frames=sum(b.size for b in blocks), interior_issues=issues,
                   note='Software journal records issued MMIO values, not hardware/USB acknowledgements. '
                        'SequenceMatcher anchors are an alignment aid; inspect nonempty gaps. '
                        'Unmatched prefix/suffix are not counted as losses.')
    index = len(exports) + 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    (args.out.parent / f'{args.out.name}-{index}.bin').write_bytes(data)
    (args.out.parent / f'{args.out.name}-{index}.json').write_text(json.dumps(summary, indent=2) + '\n')
    exports.append(summary)
    print(json.dumps(summary, indent=2))
assert exports, 'No CRC-valid TX journal recovered; do not make an alignment claim'
