#!/usr/bin/env python3
"""Enumerate media links with the exact kernel ABI.

    struct media_pad_desc   { u32 entity; u16 index; u32 flags; u32 rsv[2]; }  (20)
    struct media_link_desc  { pad_desc source; pad_desc sink; u32 flags; u32 rsv[2]; }  (52)
    struct media_links_enum { u32 entity; pad_desc *pads; link_desc *links; u32 rsv[4]; }  (40)

MEDIA_IOC_ENUM_LINKS = _IOWR('|', 0x02, struct media_links_enum) -> 0xC0287C02.
"""
import ctypes
import fcntl
import os
import struct
import sys

MEDIA_IOC_ENUM_ENTITIES = (3 << 30) | (ord("|") << 8) | 0x01 | (256 << 16)
MEDIA_IOC_ENUM_LINKS = (3 << 30) | (ord("|") << 8) | 0x02 | (40 << 16)
MAX_LINKS = 64


class PadDesc(ctypes.Structure):
    _fields_ = [("entity", ctypes.c_uint32), ("index", ctypes.c_uint16),
                ("flags", ctypes.c_uint32), ("reserved", ctypes.c_uint32 * 2)]


class LinkDesc(ctypes.Structure):
    _fields_ = [("source", PadDesc), ("sink", PadDesc),
                ("flags", ctypes.c_uint32), ("reserved", ctypes.c_uint32 * 2)]


class LinksEnum(ctypes.Structure):
    _fields_ = [("entity", ctypes.c_uint32),
                ("pads", ctypes.POINTER(PadDesc)),
                ("links", ctypes.POINTER(LinkDesc)),
                ("reserved", ctypes.c_uint32 * 4)]


def entities(fd):
    out, wanted = [], 1 << 31
    while len(out) < 256:
        buf = bytearray(256)
        struct.pack_into("<I", buf, 0, wanted)
        try:
            fcntl.ioctl(fd, MEDIA_IOC_ENUM_ENTITIES, buf)
        except OSError:
            break
        eid = struct.unpack_from("<I", buf, 0)[0]
        name = struct.unpack_from("32s", buf, 4)[0].rstrip(b"\0").decode()
        pads, links = struct.unpack_from("<HH", buf, 52)
        out.append(dict(id=eid, name=name, pads=pads, links=links))
        wanted = (eid & 0xFFFF) | (1 << 31)
    return out


fd = os.open(sys.argv[1] if len(sys.argv) > 1 else "/dev/media0", os.O_RDWR)
ents = entities(fd)
print(f"{len(ents)} entities")
names = {(e["id"] & 0xFFFF): e["name"] for e in ents}

for e in ents:
    npads = max(e["pads"], 1)
    padbuf = (PadDesc * npads)()
    linkbuf = (LinkDesc * MAX_LINKS)()
    req = LinksEnum(entity=e["id"] & 0xFFFF,
                    pads=ctypes.cast(padbuf, ctypes.POINTER(PadDesc)),
                    links=ctypes.cast(linkbuf, ctypes.POINTER(LinkDesc)))
    try:
        fcntl.ioctl(fd, MEDIA_IOC_ENUM_LINKS, req)
    except OSError as exc:
        print(f"{e['name']:24s} pads={e['pads']} links={e['links']}  ERR {exc}")
        continue
    print(f"{e['name']:24s} pads={e['pads']} links={e['links']}")
    for k in range(min(e["links"], MAX_LINKS)):
        L = linkbuf[k]
        if L.flags == 0 and L.source.entity == 0 and L.sink.entity == 0:
            continue
        print(f"    {names.get(L.source.entity, L.source.entity):24s}"
              f"[{L.source.index}] -> {names.get(L.sink.entity, L.sink.entity):24s}"
              f"[{L.sink.index}]  0x{L.flags:08x}")
os.close(fd)
