#!/usr/bin/env python3
"""Compare every FFS file in two boot images, to prove only the DTB changed."""
import hashlib
import lzma
import struct
import sys
import zlib

sys.path.insert(0, "/mnt/e/wsl-recover/work")
from bootimg import DT_GUID, walk_files, walk_sections


def layers(path):
    b = open(path, "rb").read()
    ks = struct.unpack_from("<I", b, 8)[0]
    page = struct.unpack_from("<I", b, 36)[0]
    dec = zlib.decompressobj(16 + zlib.MAX_WBITS).decompress(b[page:page + ks])
    ost = dec.find(b"_FVH") - 40
    olen = struct.unpack_from("<Q", dec, ost + 32)[0]
    outer = dec[ost:ost + olen]
    inner = None
    for f in walk_files(outer):
        if "end" in f:
            break
        if f["type"] == 0x0B:
            s = list(walk_sections(f["body"]))[0]
            raw = lzma.decompress(s["body"][20:], format=lzma.FORMAT_ALONE)
            j = raw.find(b"_FVH") - 40
            n = struct.unpack_from("<Q", raw, j + 32)[0]
            inner = raw[j:j + n]
    return outer, inner


def files(fv):
    out = {}
    for f in walk_files(fv):
        if "end" in f:
            break
        out[str(f["guid"])] = hashlib.sha256(f["body"]).hexdigest()
    return out


ao, ai = layers(sys.argv[1])
bo, bi = layers(sys.argv[2])

for label, x, y in (("outer", ao, bo), ("inner", ai, bi)):
    fx, fy = files(x), files(y)
    print(f"{label}: {len(fx)} vs {len(fy)} files")
    same = {g for g in fx if g in fy and fx[g] == fy[g]}
    diff = {g for g in fx if g in fy and fx[g] != fy[g]}
    only_x = set(fx) - set(fy)
    only_y = set(fy) - set(fx)
    print(f"  identical={len(same)} differ={len(diff)} only-old={len(only_x)} only-new={len(only_y)}")
    for g in diff:
        print(f"    DIFF {g}")
    for g in only_x | only_y:
        print(f"    ONLY {g}")
