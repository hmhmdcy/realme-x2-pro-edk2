#!/usr/bin/env python3
"""Strict newc cpio validator:每 110 字节头必须紧跟名字与 4 字节对齐数据。"""
import gzip
import sys


def walk(path):
    raw = (gzip.decompress(open(path, "rb").read())
           if path.endswith(".gz") else open(path, "rb").read())
    off = 0
    n = 0
    bad = []
    while off + 110 <= len(raw):
        if raw[off:off + 8] == b"TRAILER!":
            n += 1
            break
        if raw[off:off + 6] != b"070701":
            bad.append((off, raw[off:off + 16]))
            break
        hdr = raw[off:off + 110]
        f = [int(hdr[6 + k * 8:6 + (k + 1) * 8], 16) for k in range(13)]
        namesize, filesize = f[11], f[6]
        if namesize < 1 or 110 + namesize > len(raw) - off:
            bad.append((off, f"namesize {namesize}"))
            break
        off = (off + 110 + namesize + filesize + 3) // 4 * 4
        n += 1
    return n, bad


for p in sys.argv[1:]:
    n, bad = walk(p)
    print(f"{p}: members={n} bad={bad[:2]}")
