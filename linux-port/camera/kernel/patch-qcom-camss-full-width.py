#!/usr/bin/env python3
"""Patch the stock SM8150 CAMSS module to accept 16383-pixel RDI frames."""

import hashlib
import sys
from pathlib import Path


EXPECTED_SOURCE_SHA256 = (
    "b7edf58ebba8a252c01e17dedaf893cbd16790e284ed83727b9ea72a7dc37f20"
)
EXPECTED_SIZE = 2_936_296

# .text is at file offset 0x2000 in this exact module.  These are the five
# `mov wN, #8191` instructions used by the CAMSS try-format paths.
PATCH_OFFSETS = (0x4BCC, 0x8E18, 0xAE48, 0xEB6C, 0x20AAC)
ORIGINAL_INSTRUCTIONS = {
    bytes.fromhex("e2ff8352"),
    bytes.fromhex("e1ff8352"),
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    if len(sys.argv) != 3:
        print(f"usage: {sys.argv[0]} SRC DST", file=sys.stderr)
        return 2

    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])
    data = bytearray(src.read_bytes())

    source_hash = sha256(data)
    if source_hash != EXPECTED_SOURCE_SHA256 or len(data) != EXPECTED_SIZE:
        print(
            f"unexpected source module: sha256={source_hash} size={len(data)}",
            file=sys.stderr,
        )
        return 1

    for offset in PATCH_OFFSETS:
        instruction = bytes(data[offset : offset + 4])
        if instruction not in ORIGINAL_INSTRUCTIONS:
            print(
                f"unexpected instruction at 0x{offset:x}: {instruction.hex()}",
                file=sys.stderr,
            )
            return 1
        data[offset + 2] = 0x87

    dst.write_bytes(data)
    dst.chmod(src.stat().st_mode)

    print(f"source sha256: {source_hash}")
    print(f"patched sha256: {sha256(data)}")
    print(f"patched module: {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
