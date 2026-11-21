#!/usr/bin/env python3
"""Minimal Android boot image + UEFI FV reader/writer used by the DTB swap."""
from __future__ import annotations

import struct
import uuid

DT_GUID = uuid.UUID("25462cda-221f-47df-ac1d-259cfaa4e326")
LZ_GUID = uuid.UUID("ee4e5898-3914-4259-9d6e-dc7bd79403cf")
PAGE = 2048


def align(n: int, a: int) -> int:
    return (n + a - 1) // a * a


def fv_body_start(fv: bytes) -> int:
    return align(struct.unpack_from("<H", fv, 48)[0], 8)


def walk_files(fv: bytes):
    """Yield dicts for each FFS file, yields a {'end': n} marker at the free end."""
    off = fv_body_start(fv)
    while off + 32 <= len(fv):
        if fv[off:off + 32] == b"\xff" * 32:
            yield {"end": off}
            return
        guid = uuid.UUID(bytes_le=bytes(fv[off:off + 16]))
        typ = fv[off + 18]
        attrs = fv[off + 19]
        size = int.from_bytes(fv[off + 20:off + 23], "little")
        hs = 24
        if attrs & 1:
            size = struct.unpack_from("<Q", fv, off + 24)[0]
            hs = 32
        if size < hs or off + size > len(fv):
            yield {"end": off, "bad": True}
            return
        yield {"off": off, "guid": guid, "type": typ, "attrs": attrs,
               "size": size, "hs": hs, "body": fv[off + hs:off + size]}
        off = align(off + size, 8)


def walk_sections(blob: bytes):
    off = 0
    while off < len(blob):
        if len(blob) - off < 4:
            return
        size = int.from_bytes(blob[off:off + 3], "little")
        typ = blob[off + 3]
        hs = 4
        if size == 0xFFFFFF:
            size = struct.unpack_from("<I", blob, off + 4)[0]
            hs = 8
        if size <= hs or off + size > len(blob):
            return
        yield {"off": off, "type": typ, "hs": hs, "size": size,
               "body": blob[off + hs:off + size]}
        off = align(off + size, 4)


def fix_ffs_header(head: bytearray) -> None:
    """Recompute EFI_FFS_INTEGRITY_CHECK.Header.

    Field order is [16]=HeaderChecksum, [17]=FileChecksum, [18]=Type,
    [19]=Attributes, [20:23]=Size, [23]=State.  The image stores
    FileChecksum=0xAA ("not computed") and State=0xF8 (erase polarity).  The
    invariant every file in this image satisfies is
        sum(header bytes) % 256 == 0xA2 == 0xAA - 0x08.
    HeaderChecksum is the last byte, so it absorbs the difference.
    """
    head[16] = 0
    head[16] = (0xA2 - (sum(head) & 0xFF)) & 0xFF
    assert sum(head) % 256 == 0xA2, f"FFS header checksum {sum(head) % 256}"


def fix_fv_checksum(fv: bytearray) -> None:
    hlen = struct.unpack_from("<H", fv, 48)[0]
    struct.pack_into("<H", fv, 50, 0)
    total = sum(struct.unpack_from("<" + "H" * (hlen // 2), fv, 0)) & 0xFFFF
    struct.pack_into("<H", fv, 50, (0x10000 - total) & 0xFFFF)
    words = struct.unpack_from("<" + "H" * (hlen // 2), fv, 0)
    assert sum(words) % 0x10000 == 0


def emit_files(fv_template: bytes, files: list[dict], total: int | None = None,
               nblocks: int | None = None) -> bytes:
    """Lay out FFS files in a copy of fv_template, preserving its length."""
    total = len(fv_template) if total is None else total
    out = bytearray(b"\xff" * total)
    out[:72] = fv_template[:72]
    hlen = struct.unpack_from("<H", out, 48)[0]
    off = align(hlen, 8)
    for f in files:
        hs = 32 if f["attrs"] & 1 else 24
        body_len = len(f["body"])
        size = hs + body_len
        if f["attrs"] & 1:
            size = align(size, 8)
        if off + size > total:
            raise ValueError(f"overflow: {f['guid']} at {off} size {size}")
        head = bytearray(f["raw_head"])
        head[:16] = f["guid"].bytes_le
        head[18] = f["type"]
        head[19] = f["attrs"]
        if f["attrs"] & 1:
            head[20:23] = b"\xff\xff\xff"
            struct.pack_into("<Q", head, 24, size)
        else:
            head[20:23] = size.to_bytes(3, "little")
        fix_ffs_header(head)
        out[off:off + hs] = head
        out[off + hs:off + hs + len(f["body"])] = f["body"]
        out[off + hs + len(f["body"]):off + size] = b"\xff" * (
            size - hs - len(f["body"]))
        off = align(off + size, 8)
    struct.pack_into("<Q", out, 32, total)
    if nblocks is not None:
        blocksize = struct.unpack_from("<I", out, 56)[0]
        struct.pack_into("<I", out, 60, nblocks)
        assert blocksize * nblocks == total, (blocksize, nblocks, total)
    fix_fv_checksum(out)
    return bytes(out)
