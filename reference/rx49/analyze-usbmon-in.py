#!/usr/bin/env python3
"""Compare complete target bulk-IN usbmon payloads with an unchanged raw capture."""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re

def analyze(prefix):
    meta = json.loads(Path(str(prefix) + '.json').read_text())
    raw = Path(str(prefix) + '.raw').read_bytes()
    trace_path = Path(str(prefix) + '.usbmon')
    trace = trace_path.read_bytes()
    wanted = (int(meta['bus']), int(meta['address']))
    stream = bytearray()
    statuses, incomplete, nonzero_errors = Counter(), [], []
    complete = total = 0
    for number, line in enumerate(trace.splitlines(), 1):
        fields = line.decode('ascii').split()
        if len(fields) < 6 or fields[2] != 'C':
            continue
        address = fields[3].split(':')
        if len(address) != 4 or address[0] != 'Bi' or tuple(map(int, address[1:3])) != wanted:
            continue
        total += 1
        status, length = int(fields[4]), int(fields[5])
        statuses[str(status)] += 1
        if not length:
            continue
        if status:
            nonzero_errors.append(dict(line=number, status=status, actual=length))
        tail = fields[6:]
        data = bytes.fromhex(''.join(tail[1:])) if tail and tail[0] == '=' else b''
        if len(data) != length:
            incomplete.append(dict(line=number, actual=length, captured=len(data)))
            continue
        complete += 1
        stream.extend(data)
    exact = not incomplete and bytes(stream) == raw
    first_difference = next((i for i, (a, b) in enumerate(zip(stream, raw)) if a != b), None)
    if first_difference is None and len(stream) != len(raw):
        first_difference = min(len(stream), len(raw))
    return dict(prefix=str(prefix), bus=wanted[0], address=wanted[1],
                raw_bytes=len(raw), complete_in_data_urbs=complete,
                complete_in_bytes=len(stream), in_completions=total,
                in_statuses=dict(statuses), incomplete_payloads=incomplete,
                nonzero_status_with_data=nonzero_errors,
                full_in_stream_equals_raw=exact, first_difference=first_difference,
                raw_sha256=sha256(raw).hexdigest(), usbmon_sha256=sha256(trace).hexdigest(),
                note='usbmon is the WSL virtual HCD URB boundary, not physical USB packet/ACK evidence. '
                     'Any omitted/truncated payload prevents a full-stream equality claim.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('prefix', nargs='+', type=Path)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    rows = [analyze(p) for p in args.prefix]
    if args.out:
        args.out.write_text(json.dumps(rows, indent=2) + '\n')
    for row in rows:
        print(json.dumps(row))
