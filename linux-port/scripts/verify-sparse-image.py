#!/usr/bin/env python3
"""Verify a fastboot sparse image against its expanded raw image.

On this host /tmp is only ~4 GiB, so expanding the 111 GiB rootfs with
simg2img is not possible.  The sparse format records every data chunk with
its absolute 4 KiB block index, which is enough to compare the payloads
without writing the expansion:

    verify-sparse-image.py RAW SIMG

It checks the header geometry, that expanded size equals the raw file size,
and that every data chunk's bytes match the same offset in the raw image.
"""

from __future__ import annotations

import argparse
import struct
import sys

MAGIC = 0xED26FF3A
CHUNK_TYPE_RAW = 0xCAC1
CHUNK_TYPE_FILL = 0xCAC2
CHUNK_TYPE_DONT_CARE = 0xCAC3
FILE_HEADER_SIZE = 28
CHUNK_HEADER_SIZE = 12


def expanded_size(sparse_path: str, block_size: int, total_blocks: int) -> int:
    return block_size * total_blocks


def verify(raw_path: str, sparse_path: str) -> int:
    errors: list[str] = []
    with open(sparse_path, "rb") as sf, open(raw_path, "rb") as rf:
        header = sf.read(FILE_HEADER_SIZE)
        if len(header) != FILE_HEADER_SIZE:
            print("sparse: truncated file header", file=sys.stderr)
            return 1
        magic, major, minor, file_hdr_sz, chunk_hdr_sz = struct.unpack(
            "<IHHHH", header[:12]
        )
        block_size, total_blocks, total_chunks, _checksum = struct.unpack(
            "<IIII", header[12:28]
        )
        if magic != MAGIC:
            print("sparse: bad magic", file=sys.stderr)
            return 1
        if file_hdr_sz != FILE_HEADER_SIZE or chunk_hdr_sz != CHUNK_HEADER_SIZE:
            print("sparse: unexpected header sizes", file=sys.stderr)
            return 1

        raw_size = __import__("os").stat(raw_path).st_size
        expected = expanded_size(sparse_path, block_size, total_blocks)
        if expected != raw_size:
            errors.append(
                f"expanded size {expected} != raw size {raw_size}"
            )

        block = 0
        chunks = 0
        data_bytes = 0
        while chunks < total_chunks:
            chunk = sf.read(CHUNK_HEADER_SIZE)
            if len(chunk) != CHUNK_HEADER_SIZE:
                errors.append(f"chunk {chunks}: truncated header")
                break
            # Android sparse header: chunk_sz is the block count, total_sz is
            # the byte size including the 12-byte header.
            ctype, _reserved, cblocks, cbytes = struct.unpack("<HHII", chunk)
            chunks += 1
            payload_size = cbytes - CHUNK_HEADER_SIZE
            if ctype == CHUNK_TYPE_DONT_CARE:
                block += cblocks
                continue
            if ctype == CHUNK_TYPE_FILL:
                if payload_size != 4:
                    errors.append(f"chunk {chunks}: bad fill size {payload_size}")
                    break
                fill = sf.read(4) * (cblocks * block_size // 4)
            elif ctype == CHUNK_TYPE_RAW:
                fill = sf.read(payload_size)
                if len(fill) != payload_size:
                    errors.append(f"chunk {chunks}: truncated payload")
                    break
            else:
                errors.append(f"chunk {chunks}: unknown type {ctype:#x}")
                break

            rf.seek(block * block_size)
            raw = rf.read(len(fill))
            if raw != fill:
                errors.append(f"chunk {chunks}: payload differs at block {block}")
                break
            data_bytes += len(fill)
            block += cblocks

        if block != total_blocks:
            errors.append(f"expanded {block} blocks, expected {total_blocks}")

    print(
        f"sparse: {chunks} chunks, block_size={block_size}, "
        f"blocks={total_blocks}, data={data_bytes} bytes, "
        f"expanded={expected} bytes"
    )
    if errors:
        for error in errors:
            print(f"FAIL {error}", file=sys.stderr)
        return 1
    print("OK: sparse payload is byte-identical to the raw image")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("raw")
    p.add_argument("sparse")
    a = p.parse_args()
    return verify(a.raw, a.sparse)


if __name__ == "__main__":
    raise SystemExit(main())
