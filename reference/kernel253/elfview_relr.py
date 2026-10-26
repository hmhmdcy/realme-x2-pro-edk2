"""Extend the read-only stage241 ELF viewer with Android/standard RELR.

RELR stores relocation addresses as a direct address or a 63-slot bitmap;
addends remain in the target word. Does not load or execute vendor code.
"""
from pathlib import Path
import struct
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'kernel241'))
from elfview import Elf


def relocation_addresses(entries):
    where = None
    for value in entries:
        if value & 1:
            if where is None:
                raise ValueError('RELR bitmap precedes direct address')
            for bit in range(63):
                if value & (1 << (bit + 1)):
                    yield where + bit * 8
            where += 63 * 8
        else:
            if value % 8:
                raise ValueError('Unaligned RELR address')
            yield value
            where = value + 8


class RelrElf(Elf):
    def __init__(self, path):
        super().__init__(path)
        self.relr_count = 0
        for section in self.sections:
            if section['type'] not in (19, 0x6fffff00):
                continue
            if section['size'] % 8 or section['entsize'] != 8:
                raise ValueError('Invalid ELF64 RELR entry size')
            data = self.section_bytes(section)
            words = struct.unpack('<' + 'Q' * (len(data) // 8), data)
            for address in relocation_addresses(words):
                if address in self.relocs:
                    raise ValueError('Duplicate RELR/RELA target')
                addend = struct.unpack('<Q', self.read(address, 8))[0]
                self.relocs[address] = dict(kind=1027, symbol=self.syms[0], addend=addend)
                self.relr_count += 1


def selftest():
    assert list(relocation_addresses([0x1000, 1 | 2 | 8, 0x2000])) == [0x1000, 0x1008, 0x1018, 0x2000]
    assert list(relocation_addresses([0x1000, 1, 3])) == [0x1000, 0x1200]
    for words in ([3], [0x1002]):
        try:
            list(relocation_addresses(words))
        except ValueError:
            pass
        else:
            raise AssertionError('Malformed RELR accepted')
    return dict(direct_bitmap_empty_bitmap_and_rejection=True)


if __name__ == '__main__':
    import json
    print(json.dumps(selftest()))
