#!/usr/bin/env python3
"""Read selected named structure offsets from the already matched local PDB.

Fail on unsupported selected leaf records, never infer a member offset from
another driver release. This is a narrow C-structure reader, not a full PDB API.
"""
import argparse
import json
from pathlib import Path
import struct
import runpy
Msf = runpy.run_path(str(Path(__file__).with_name('inspect-qcusbser.py')))['Msf']


def numeric(data, pos):
    number, = struct.unpack_from('<H', data, pos)
    if number < 0x8000:
        return number, pos + 2
    formats = {0x8000: 'b', 0x8001: 'h', 0x8002: 'H', 0x8003: 'i', 0x8004: 'I',
               0x8009: 'q', 0x800a: 'Q'}
    fmt = '<' + formats[number]
    return struct.unpack_from(fmt, data, pos + 2)[0], pos + 2 + struct.calcsize(fmt)


def inspect(path):
    tpi = Msf(path).streams[2]
    header, first, last, size = struct.unpack_from('<4I', tpi, 4)
    records, pos, index = {}, header, first
    while pos < header + size:
        length, kind = struct.unpack_from('<HH', tpi, pos)
        assert pos + 2 + length <= len(tpi)
        records[index] = (kind, tpi[pos + 4:pos + 2 + length])
        index += 1
        pos += 2 + length
    assert pos == header + size and index == last

    def fields(index):
        kind, data = records[index]
        assert kind == 0x1203, hex(kind)  # LF_FIELDLIST
        result, pos = [], 0
        while pos < len(data):
            if data[pos] >= 0xf0:
                pad = data[pos] & 0xf
                assert pad > 0
                pos += pad
                continue
            leaf, = struct.unpack_from('<H', data, pos)
            if leaf == 0x1404:  # LF_INDEX continuation
                continuation, = struct.unpack_from('<I', data, pos + 4)
                result.extend(fields(continuation))
                pos += 8
                continue
            assert leaf == 0x150d, ('Unsupported field leaf', hex(leaf))
            attrs, member_type = struct.unpack_from('<HI', data, pos + 2)
            offset, pos = numeric(data, pos + 8)
            end = data.index(0, pos)
            result.append(dict(name=data[pos:end].decode(), offset=offset, type=f'{member_type:08x}'))
            pos = end + 1
        return result

    result = []
    for index, (kind, data) in records.items():
        if kind not in (0x1504, 0x1505):  # LF_CLASS / LF_STRUCTURE
            continue
        count, properties, fieldlist = struct.unpack_from('<HHI', data)
        if properties & 0x80:  # forward declaration
            continue
        length, pos = numeric(data, 16)
        name = data[pos:data.index(0, pos)].decode()
        if not any(s in name for s in ('DEVICE_EXTENSION', 'SERIAL_STATUS', 'SERIALPERF_STATS')):
            continue
        members = fields(fieldlist)
        assert len(members) == count
        result.append(dict(name=name, type=f'{index:08x}', size=length, members=members))
    assert result, 'No selected complete structures present'
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('pdb', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    # Import the hyphenated companion without requiring a file rename.
    result = inspect(args.pdb)
    args.out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps([dict(name=r['name'], size=r['size'], members=len(r['members'])) for r in result], indent=2))
