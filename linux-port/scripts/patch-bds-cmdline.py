#!/usr/bin/env python3
"""Patch the samurai LoadOptions string in BdsDxe.efi without relinking it."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


TAG = "console=tty0"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def find_cmdline(data: bytes) -> tuple[int, int, str]:
    needle = TAG.encode("utf-16le")
    matches = []
    offset = 0
    while True:
        offset = data.find(needle, offset)
        if offset < 0:
            break
        end = offset
        while end + 1 < len(data) and data[end:end + 2] != b"\0\0":
            end += 2
        if end + 1 >= len(data):
            raise SystemExit("unterminated UTF-16 command line")
        text = data[offset:end].decode("utf-16le")
        matches.append((offset, end, text))
        offset = end + 2
    production = [item for item in matches if "earlycon" not in item[2]]
    if len(production) != 1:
        raise SystemExit(
            f"expected one production command line, found {len(production)}"
        )
    return production[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--drop", action="append", default=[])
    parser.add_argument("--loglevel", type=int)
    args = parser.parse_args()

    data = bytearray(args.input.read_bytes())
    start, end, old = find_cmdline(bytes(data))
    new = old
    for token in args.drop:
        if token not in new:
            raise SystemExit(f"token not present: {token}")
        new = new.replace(token, " " * len(token))
    if args.loglevel is not None:
        for level in range(10):
            new = new.replace(f"loglevel={level}", f"loglevel={args.loglevel}")

    if len(new) != len(old):
        raise SystemExit("command-line length changed")
    encoded = new.encode("utf-16le")
    if len(encoded) != end - start:
        raise SystemExit("encoded command-line length changed")
    if any(not value.isprintable() for value in new):
        raise SystemExit("command line contains non-printable characters")
    data[start:end] = encoded
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(data)

    print(f"old_sha256={sha256(args.input.read_bytes())}")
    print(f"new_sha256={sha256(data)}")
    print(f"old_cmdline={old!r}")
    print(f"new_cmdline={new!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
