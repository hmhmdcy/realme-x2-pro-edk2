"""Small read-only ELF64/AArch64 viewer, including Android APS2 RELA."""
import struct
import subprocess
from pathlib import Path


class Elf:
    def __init__(self, path):
        self.path = Path(path)
        self.data = self.path.read_bytes()
        assert self.data[:6] == b'\x7fELF\x02\x01'
        hdr = struct.unpack_from('<16sHHIQQQIHHHHHH', self.data)
        assert hdr[2] == 183 and hdr[11] == 64
        raw = [struct.unpack_from('<IIQQQQIIQQ', self.data, hdr[6] + i * 64)
               for i in range(hdr[12])]
        names = self.data[raw[hdr[13]][4]:raw[hdr[13]][4] + raw[hdr[13]][5]]
        self.sections = []
        for s in raw:
            self.sections.append(dict(name=self.zstring(names, s[0]), type=s[1], flags=s[2],
                addr=s[3], offset=s[4], size=s[5], link=s[6], info=s[7], align=s[8], entsize=s[9]))
        self.syms = []
        for sec in self.sections:
            if sec['type'] != 11:
                continue
            strings = self.section_bytes(self.sections[sec['link']])
            for offset in range(sec['offset'], sec['offset'] + sec['size'], 24):
                name, info, other, shndx, value, size = struct.unpack_from('<IBBHQQ', self.data, offset)
                self.syms.append(dict(name=self.zstring(strings, name), value=value, size=size,
                                      type=info & 15, shndx=shndx))
        demangled = subprocess.check_output(['c++filt'], input='\n'.join(s['name'] for s in self.syms) + '\n', text=True).splitlines()
        assert len(demangled) == len(self.syms)
        for s, name in zip(self.syms, demangled):
            s['demangled'] = name
        self.relocs = {}
        self.packed_count = 0
        for sec in self.sections:
            records = []
            if sec['type'] == 4:
                records = [struct.unpack_from('<QQq', self.data, p)
                           for p in range(sec['offset'], sec['offset'] + sec['size'], 24)]
            elif sec['type'] == 0x60000002:
                blob = self.section_bytes(sec)
                assert blob[:4] == b'APS2'
                records = list(self.aps2(blob))
                self.packed_count += len(records)
            for addr, info, addend in records:
                symbol, kind = info >> 32, info & 0xffffffff
                assert addr not in self.relocs
                assert symbol < len(self.syms)
                self.relocs[addr] = dict(kind=kind, symbol=self.syms[symbol], addend=addend)

    @staticmethod
    def zstring(data, offset):
        end = data.index(0, offset)
        return data[offset:end].decode(errors='replace')

    def section_bytes(self, section):
        return self.data[section['offset']:section['offset'] + section['size']]

    @staticmethod
    def aps2(blob):
        pos = 4

        def sleb():
            nonlocal pos
            value = shift = 0
            while True:
                byte = blob[pos]
                pos += 1
                value |= (byte & 127) << shift
                shift += 7
                assert shift <= 70
                if not byte & 128:
                    return value - (1 << shift) if byte & 64 else value

        count, address = sleb(), sleb()
        done = addend = 0
        while done < count:
            size, flags = sleb(), sleb()
            assert 0 < size <= count - done and flags & ~15 == 0
            delta = sleb() if flags & 2 else None
            info = sleb() if flags & 1 else None
            if flags & 8:
                if flags & 4:
                    addend += sleb()
            else:
                assert not flags & 4
                addend = 0
            for _ in range(size):
                address += delta if flags & 2 else sleb()
                item_info = info if flags & 1 else sleb()
                if flags & 8 and not flags & 4:
                    addend += sleb()
                yield address, item_info, addend
                done += 1
        assert done == count and pos == len(blob)

    def read(self, address, count):
        for sec in self.sections:
            if sec['type'] != 8 and sec['addr'] <= address and address + count <= sec['addr'] + sec['size']:
                offset = sec['offset'] + address - sec['addr']
                return self.data[offset:offset + count]
        raise ValueError(hex(address))

    def pointer(self, address):
        relocation = self.relocs.get(address)
        if relocation:
            assert relocation['kind'] in (257, 1025, 1026, 1027)
            s = relocation['symbol']
            return dict(value=s['value'] + relocation['addend'], name=s['demangled'],
                        external=s['shndx'] == 0 and bool(s['name']), relocation=relocation['kind'])
        return dict(value=struct.unpack('<Q', self.read(address, 8))[0], name='', external=False)

    def describe(self, address):
        exact = [s for s in self.syms if s['shndx'] and s['value'] == address]
        if exact:
            return exact[0]['demangled']
        within = [s for s in self.syms if s['shndx'] and s['value'] <= address < s['value'] + s['size']]
        return min(within, key=lambda s:s['size'])['demangled'] if within else hex(address)
