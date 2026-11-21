#!/usr/bin/env python3
"""Replace the OS DTB in the samurai boot image and rebuild every checksum.

The layout algorithm in bootimg.emit_files is self-tested: rebuilding the live
inner FV with the *same* DTB reproduces it byte for byte.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import lzma
import struct
import sys
import uuid
import zlib

sys.path.insert(0, "/mnt/e/wsl-recover/work")
from bootimg import (DT_GUID, LZ_GUID, PAGE, align, emit_files, fix_fv_checksum,
                     walk_files, walk_sections)

DICT = 1 << 24
TAG = 0xAA


def lzma_alone(data: bytes) -> bytes:
    """Encode like the image does: 13-byte props header, no end-of-stream marker."""
    comp = lzma.LZMACompressor(
        format=lzma.FORMAT_RAW,
        filters=[{"id": lzma.FILTER_LZMA1, "dict_size": DICT, "lc": 3, "lp": 0,
                  "pb": 2, "mode": lzma.MODE_NORMAL, "nice_len": 273,
                  "mf": lzma.MF_BT4, "depth": 0}],
    )
    raw = comp.compress(data) + comp.flush()
    return b"\x5d" + DICT.to_bytes(4, "little") + len(data).to_bytes(8, "little") + raw


def collect(fv):
    files = []
    for f in walk_files(fv):
        if "end" in f:
            return files, f["end"]
        d = {k: f[k] for k in ("off", "guid", "type", "attrs", "hs", "size")}
        d["body"] = f["body"]
        d["raw_head"] = bytes(fv[f["off"]:f["off"] + f["hs"]])
        files.append(d)
    return files, None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--boot", required=True)
    ap.add_argument("--dtb", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    src = open(a.boot, "rb").read()
    assert src[:8] == b"ANDROID!"
    ksize, = struct.unpack_from("<I", src, 8)
    assert struct.unpack_from("<I", src, 36)[0] == PAGE
    assert struct.unpack_from("<I", src, 16)[0] in (0, 1), "expect empty ramdisk"

    kd = zlib.decompressobj(16 + zlib.MAX_WBITS)
    dec = kd.decompress(src[PAGE:PAGE + ksize])
    trailer = kd.unused_data
    assert trailer[:4] == bytes.fromhex("d00dfeed")
    print(f"kernel region {ksize}: gzip {ksize - len(trailer)} trailer {len(trailer)}")

    ost = dec.find(b"_FVH") - 40
    olen, = struct.unpack_from("<Q", dec, ost + 32)
    assert ost + olen == len(dec)
    pre, outer = dec[:ost], dec[ost:]

    ofiles, oend = collect(outer)
    hin, oi = None, None
    for i, f in enumerate(ofiles):
        if f["type"] == 0x0B:
            s = list(walk_sections(f["body"]))[0]
            hin = lzma.decompress(s["body"][20:], format=lzma.FORMAT_ALONE)
            oi = i
    assert hin is not None
    print(f"outer FV {olen}: FVMAIN off={ofiles[oi]['off']} "
          f"body={len(ofiles[oi]['body'])} free@{oend}")

    ist = hin.find(b"_FVH") - 40
    ilen, = struct.unpack_from("<Q", hin, ist + 32)
    ipre, inner = hin[:ist], hin[ist:ist + ilen]
    ifiles, iend = collect(inner)
    print(f"inner FV {ilen}: {len(ifiles)} files, free@{iend}, "
          f"trailing {len(inner) - iend} bytes")

    di = next(i for i, f in enumerate(ifiles) if f["guid"] == DT_GUID)
    old_sec = list(walk_sections(ifiles[di]["body"]))[0]
    old_payload = old_sec["body"]
    print(f"DTB file off={ifiles[di]['off']} size={ifiles[di]['size']} "
          f"payload={len(old_payload)} md5={hashlib.md5(old_payload).hexdigest()}")

    new = open(a.dtb, "rb").read()
    assert new[:4] == bytes.fromhex("d00dfeed")
    print(f"new DTB {len(new)} bytes md5={hashlib.md5(new).hexdigest()}")
    ifiles[di]["body"] = (4 + len(new)).to_bytes(3, "little") + b"\x19" + new

    blocksize = struct.unpack_from("<I", inner, 56)[0]
    nblocks = struct.unpack_from("<I", inner, 60)[0]

    def grow(files, tmpl):
        prev = None
        cur = tmpl
        for extra in range(0, 5):
            target = len(tmpl) + extra * blocksize
            try:
                built = emit_files(cur, files, total=target, nblocks=nblocks + extra)
                return built, extra, target
            except ValueError as exc:
                prev = exc
                continue
        raise SystemExit(f"inner FV cannot fit the grown DTB: {prev}")

    new_inner, extra, target = grow(ifiles, inner)
    if extra:
        print(f"inner FV grew by {extra} block(s) -> {target} bytes")
    else:
        print(f"inner rebuild ok: {len(new_inner)} bytes (free tail {len(inner) - iend})")

    payload = lzma_alone(ipre + new_inner)
    guid_hdr = LZ_GUID.bytes_le + struct.pack("<HH", 20, 0x0001)
    sec = bytearray((4 + len(guid_hdr) + len(payload)).to_bytes(3, "little") + b"\x02")
    sec += guid_hdr + payload
    print(f"FVMAIN body {len(guid_hdr) + len(payload) + 4} "
          f"(was {len(ofiles[oi]['body'])})")
    ofiles[oi]["body"] = bytes(sec)
    new_outer = emit_files(outer, ofiles)
    assert len(new_outer) == len(outer)

    new_dec = pre + new_outer
    assert len(new_dec) == len(dec)
    gz = gzip.compress(new_dec, compresslevel=6, mtime=0)
    region = gz + trailer
    print(f"gzip {ksize - len(trailer)} -> {len(gz)}; region {len(region)}")
    if len(region) > len(src) - PAGE:
        raise SystemExit("region too large")

    out = bytearray(src)
    out[PAGE:PAGE + ksize] = b"\x00" * ksize
    out[PAGE:PAGE + len(region)] = region
    struct.pack_into("<I", out, 8, len(region))
    open(a.out, "wb").write(out)
    print("written", a.out)

    # ---------- verification ----------
    v = open(a.out, "rb").read()
    vk, = struct.unpack_from("<I", v, 8)
    vt = zlib.decompressobj(16 + zlib.MAX_WBITS)
    vd = vt.decompress(v[PAGE:PAGE + vk])
    assert vt.unused_data == trailer, "trailer changed"
    vo = vd[ost:ost + olen]
    hl = struct.unpack_from("<H", vo, 48)[0]
    assert sum(struct.unpack_from("<" + "H" * (hl // 2), vo, 0)) % 0x10000 == 0
    print("outer FV checksum  : ok")

    f2 = None
    for f in walk_files(vo):
        if "end" in f:
            break
        if f["type"] == 0x0B:
            f2 = f
    s = list(walk_sections(f2["body"]))[0]
    vi = lzma.decompress(s["body"][20:], format=lzma.FORMAT_ALONE)
    j = vi.find(b"_FVH") - 40
    l2, = struct.unpack_from("<Q", vi, j + 32)
    vinner = vi[j:j + l2]
    hl2 = struct.unpack_from("<H", vinner, 48)[0]
    assert sum(struct.unpack_from("<" + "H" * (hl2 // 2), vinner, 0)) % 0x10000 == 0
    print("inner FV checksum  : ok")

    for f in walk_files(vinner):
        if "end" in f:
            break
        if f["guid"] == DT_GUID:
            got = list(walk_sections(f["body"]))[0]["body"]
            assert got == new, "DTB payload differs after rebuild"
            print(f"DTB payload        : identical ({len(got)} bytes)")
            break
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
