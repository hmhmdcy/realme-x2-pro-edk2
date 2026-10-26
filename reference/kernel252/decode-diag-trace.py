#!/usr/bin/env python3
"""Read-only decoder for this device's diag_mdlog syscall trace.

Raw frames may contain private data. Keep --private-output outside the repo.
Validates complete read results, USER_SPACE_DATA_TYPE framing and HDLC CRC.
Does not infer RF field names or send commands to a device.
"""
import argparse
import collections
import json
from pathlib import Path
import re
import struct


def crc16(data):
    value = 0xffff
    for byte in data:
        value ^= byte
        for _ in range(8):
            value = (value >> 1) ^ 0x8408 if value & 1 else value >> 1
    return value ^ 0xffff


def decode(path):
    diag = ''.join('\\x%02x' % c for c in b'/dev/diag')
    pending, reads, errors = {}, [], []
    for number, line in enumerate(path.open(encoding='utf-8'), 1):
        match = re.match(r'^(\d+)\s+[0-9.]+\s+(.*)', line.rstrip('\n'))
        if not match:
            continue
        tid, body = int(match[1]), match[2]
        if body.endswith('<unfinished ...>'):
            pending[tid] = (number, body[:-len('<unfinished ...>')])
            continue
        resumed = re.match(r'<\.\.\. \w+ resumed>(.*)', body)
        if resumed:
            previous = pending.pop(tid, None)
            if previous is None:
                continue
            number, body = previous[0], previous[1] + resumed[1]
        if not re.match(r'read\(\d+<' + re.escape(diag) + r'>', body):
            continue
        encoded = re.search(r'"((?:\\x[0-9a-f]{2})+)"', body)
        result = re.search(r'\)\s+=\s+(\d+)\s', body)
        if not encoded or not result:
            continue
        raw = bytes.fromhex(encoded[1].replace('\\x', ''))
        if len(raw) != int(result[1]):
            errors.append(dict(line=number, reason='truncated_read'))
            continue
        reads.append(raw)
    streams = collections.defaultdict(bytearray)
    field_count = 0
    for raw in reads:
        if len(raw) < 8 or struct.unpack_from('<I', raw)[0] != 32:
            continue
        count, pos = struct.unpack_from('<I', raw, 4)[0], 8
        for _ in range(count):
            if pos + 4 > len(raw):
                raise ValueError('Truncated DIAG data field')
            length = struct.unpack_from('<I', raw, pos)[0]
            pos += 4
            token = 0
            if length & 0x80000000:
                token = struct.unpack('<i', struct.pack('<I', length))[0]
                length = struct.unpack_from('<I', raw, pos)[0]
                pos += 4
            if length > len(raw) - pos:
                raise ValueError('DIAG data length exceeds complete read')
            streams[token] += raw[pos:pos + length]
            field_count += 1
            pos += length
        if pos != len(raw):
            raise ValueError('Unexpected DIAG trailing bytes')
    frames, invalid, trailing = [], 0, 0
    for token, stream in streams.items():
        pieces = bytes(stream).split(b'\x7e')
        trailing += len(pieces[-1])
        for piece in pieces[:-1]:
            if not piece:
                continue
            raw, pos = bytearray(), 0
            while pos < len(piece):
                byte, pos = piece[pos], pos + 1
                if byte == 0x7d:
                    if pos == len(piece):
                        break
                    byte, pos = piece[pos] ^ 0x20, pos + 1
                raw.append(byte)
            if len(raw) < 3 or crc16(raw[:-2]) != struct.unpack_from('<H', raw, len(raw) - 2)[0]:
                invalid += 1
                continue
            frames.append(dict(token=token, payload_hex=raw[:-2].hex()))
    payloads = [bytes.fromhex(x['payload_hex']) for x in frames]
    logs = []
    for raw in payloads:
        if raw[0] != 0x10:
            continue
        if len(raw) < 16:
            raise ValueError('Short DIAG log envelope')
        outer, inner, code = struct.unpack_from('<HHH', raw, 2)
        if outer != inner or inner + 4 != len(raw):
            raise ValueError('DIAG log envelope length mismatch')
        logs.append(dict(code=code, payload_hex=raw.hex()))
    summary = dict(reads=len(reads), read_errors=errors,
        data_types=dict(collections.Counter(hex(struct.unpack_from('<I', b)[0]) for b in reads)),
        data_fields=field_count, valid_crc_frames=len(frames), invalid_crc_frames=invalid,
        trailing_partial_bytes=trailing,
        commands=dict(collections.Counter(hex(b[0]) for b in payloads)),
        log_counts=dict(collections.Counter(hex(x['code']) for x in logs)))
    return frames, logs, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trace', type=Path)
    parser.add_argument('--private-output', type=Path, required=True)
    args = parser.parse_args()
    frames, logs, summary = decode(args.trace)
    args.private_output.mkdir(parents=True, exist_ok=True)
    for name, value in [('frames-private.json', frames), ('logs-private.json', logs), ('summary.json', summary)]:
        (args.private_output / name).write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
