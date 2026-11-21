#!/usr/bin/env python3
"""Minimal, correct newc cpio reader/writer (WSL has no cpio binary).

Two paddings matter and are easy to miss:
  1. after header+name, to the next 4-byte boundary;
  2. after file data, to the next 4-byte boundary.
Skipping (1) desyncs the whole archive, which is exactly what happened when
the regulatory.db insert was first attempted.
"""
import gzip
import io


pad4 = lambda n: (-n) % 4


def entries(raw):
    off = 0
    while off + 110 <= len(raw):
        if raw[off:off + 6] != b"070701":
            raise ValueError(f"bad magic at {off}: {raw[off:off+16]!r}")
        hdr = raw[off:off + 110]
        f = [int(hdr[6 + k * 8:6 + (k + 1) * 8], 16) for k in range(13)]
        namesize, filesize = f[11], f[6]
        name = raw[off + 110:off + 110 + namesize - 1].decode()
        if name == "TRAILER!!!":
            return
        data_at = off + 110 + namesize + pad4(110 + namesize)
        yield (name, hdr, raw[data_at:data_at + filesize])
        off = data_at + filesize + pad4(filesize)


header = lambda ino, mode, size, namesize: (
    b"070701"
    + b"%08X" % ino + b"%08X" % mode + b"%08X" % 0 + b"%08X" % 0
    + b"%08X" % 1 + b"%08X" % 0 + b"%08X" % size
    + b"%08X" % 0 + b"%08X" % 0 + b"%08X" % 0 + b"%08X" % 0
    + b"%08X" % namesize + b"%08X" % 0)


def blob(name, data, ino, mode=0o100644):
    h = header(ino, mode, len(data), len(name) + 1)
    out = h + name.encode() + b"\0"
    out += b"\0" * pad4(len(h) + len(name) + 1)
    out += data
    out += b"\0" * pad4(len(data))
    return out


_ = (gzip, io)
