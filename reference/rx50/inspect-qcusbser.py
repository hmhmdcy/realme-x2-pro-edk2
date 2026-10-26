#!/usr/bin/env python3
"""Read-only exact PE/PDB identification and selected function disassembly.

Uses LLVM's MSF 7 / DBI / S_PUB32 layouts. No guessed symbol binding: GUID,
age, section headers and AMD64 exception-directory bounds must agree.
Requires pefile and capstone; never loads or modifies a driver.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import uuid
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_64


class Msf:
    def __init__(self, path):
        self.data = Path(path).read_bytes()
        assert self.data[:32] == b'Microsoft C/C++ MSF 7.00\r\n\x1aDS\0\0\0'
        self.block, free, total, size, unknown, blockmap = struct.unpack_from('<6I', self.data, 32)
        assert self.block in (512, 1024, 2048, 4096)
        assert total * self.block == len(self.data)
        pages = (size + self.block - 1) // self.block
        assert pages * 4 <= self.block
        directory = self.join(struct.unpack_from('<' + 'I' * pages, self.data, blockmap * self.block))[:size]
        n, = struct.unpack_from('<I', directory)
        sizes = struct.unpack_from('<' + 'I' * n, directory, 4)
        self.streams = []
        off = 4 + 4 * n
        for length in sizes:
            pages = 0 if length == 0xffffffff else (length + self.block - 1) // self.block
            indices = struct.unpack_from('<' + 'I' * pages, directory, off)
            off += 4 * pages
            self.streams.append(None if length == 0xffffffff else self.join(indices)[:length])
        assert off == size

    def join(self, blocks):
        assert all((index + 1) * self.block <= len(self.data) for index in blocks)
        return b''.join(self.data[index * self.block:(index + 1) * self.block] for index in blocks)


def inspect(binary, pdb, names, out):
    pe = pefile.PE(str(binary))
    assert pe.FILE_HEADER.Machine == 0x8664
    cv = [d for d in pe.DIRECTORY_ENTRY_DEBUG if d.struct.Type == 2]
    assert len(cv) == 1
    cv = pe.__data__[cv[0].struct.PointerToRawData:cv[0].struct.PointerToRawData + cv[0].struct.SizeOfData]
    assert cv[:4] == b'RSDS'
    pe_guid, pe_age = str(uuid.UUID(bytes_le=cv[4:20])), struct.unpack_from('<I', cv, 20)[0]
    msf = Msf(pdb)
    info = msf.streams[1]
    pdb_guid, pdb_age = str(uuid.UUID(bytes_le=info[12:28])), struct.unpack_from('<I', info, 8)[0]
    assert (pe_guid, pe_age) == (pdb_guid, pdb_age), 'PDB identity mismatch'
    dbi = msf.streams[3]
    assert struct.unpack_from('<I', dbi, 8)[0] == pdb_age
    symstream = struct.unpack_from('<H', dbi, 20)[0]
    # Use the PDB section-header stream to prevent silently assuming PE numbering.
    mod, contribution, sectionmap, source, typeserver = struct.unpack_from('<5i', dbi, 24)
    optional_size, ec = struct.unpack_from('<2i', dbi, 48)
    optional_offset = 64 + mod + contribution + sectionmap + source + typeserver + ec
    section_stream = struct.unpack_from('<H', dbi, optional_offset + 10)[0]
    headers = msf.streams[section_stream]
    assert len(headers) == 40 * len(pe.sections)
    for i, section in enumerate(pe.sections):
        assert headers[i * 40:(i + 1) * 40] == section.__pack__(), 'Section header mismatch'
    symbols, unmapped, offset = [], [], 0
    records = msf.streams[symstream]
    while offset < len(records):
        length, kind = struct.unpack_from('<HH', records, offset)
        assert length >= 2 and offset + 2 + length <= len(records)
        body = records[offset + 4:offset + 2 + length]
        if kind == 0x110e:  # S_PUB32
            flags, relative, segment = struct.unpack_from('<IIH', body)
            name = body[10:].split(b'\0', 1)[0].decode('utf-8')
            if not 1 <= segment <= len(pe.sections):
                # Linker/absolute symbols outside retained PE sections are not
                # evidence of executable code. Retain their names, do not bind.
                unmapped.append(dict(name=name, segment=segment, relative=relative, flags=flags))
                offset += 2 + length
                continue
            rva = pe.sections[segment - 1].VirtualAddress + relative
            symbols.append(dict(name=name, rva=rva, flags=flags))
        offset += 2 + length
    symbols.sort(key=lambda row: (row['rva'], row['name']))
    report = dict(binary_sha256=hashlib.sha256(Path(binary).read_bytes()).hexdigest(),
                  pdb_sha256=hashlib.sha256(Path(pdb).read_bytes()).hexdigest(),
                  guid=pe_guid, age=pe_age, symbols=len(symbols),
                  identity_matches=True, section_headers_match=True,
                  unmapped_symbols=unmapped, functions=[])
    out.mkdir(parents=True, exist_ok=True)
    (out / 'qcusbser-symbols.json').write_text(json.dumps(symbols, indent=2) + '\n')
    engine = Cs(CS_ARCH_X86, CS_MODE_64)
    by_rva = {s['rva']: s['name'] for s in symbols}
    for name in names:
        found = [s for s in symbols if s['name'] == name]
        assert len(found) == 1, (name, len(found))
        start = found[0]['rva']
        runtime = [r.struct for r in pe.DIRECTORY_ENTRY_EXCEPTION if r.struct.BeginAddress == start]
        assert len(runtime) == 1, ('No exact exception-directory bounds', name, hex(start))
        end = runtime[0].EndAddress
        code = pe.get_data(start, end - start)
        instructions = list(engine.disasm(code, start))
        assert sum(i.size for i in instructions) == len(code), 'Incomplete disassembly'
        lines = []
        for i in instructions:
            annotation = ''
            if i.mnemonic in ('call', 'jmp') and i.op_str.startswith('0x'):
                target = int(i.op_str, 16)
                if target in by_rva:
                    annotation = ' ; ' + by_rva[target]
            lines.append(f'{i.address:08x} {i.bytes.hex(" "):24s} {i.mnemonic:8s} {i.op_str}{annotation}')
        filename = name + '.asm.txt'
        (out / filename).write_text('\n'.join(lines) + '\n')
        report['functions'].append(dict(name=name, start_rva=f'{start:08x}', end_rva=f'{end:08x}',
                                        size=len(code), code_sha256=hashlib.sha256(code).hexdigest(),
                                        disassembly=filename))
    (out / 'qcusbser-identity.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('binary', type=Path)
    parser.add_argument('pdb', type=Path)
    parser.add_argument('--function', action='append', default=[])
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(inspect(args.binary, args.pdb, args.function, args.out), indent=2))
