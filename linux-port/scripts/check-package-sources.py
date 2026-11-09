#!/usr/bin/env python3
"""Validate APKBUILD source names against the local sha512sums block."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("package", type=Path)
    args = parser.parse_args()

    apkbuild = args.package / "APKBUILD"
    text = apkbuild.read_text(encoding="utf-8")
    source_match = re.search(r'^source="(.*?)"', text, re.M | re.S)
    sums_match = re.search(r'^sha512sums="\n(.*?)\n"', text, re.M | re.S)
    if not source_match or not sums_match:
        print(f"{apkbuild}: source or sha512sums block missing")
        return 1

    sources = source_match.group(1).split()
    sums = {
        name: digest
        for digest, name in re.findall(
            r"^([0-9a-f]{128})\s+(\S+)$", sums_match.group(1), re.M
        )
    }
    errors: list[str] = []
    for name in sources:
        path = args.package / name
        if not path.is_file():
            errors.append(f"missing source: {name}")
            continue
        if name not in sums:
            errors.append(f"missing sha512: {name}")
            continue
        digest = hashlib.sha512(path.read_bytes()).hexdigest()
        if digest != sums[name]:
            errors.append(f"sha512 mismatch: {name}")
    for name in sums:
        if name not in sources:
            errors.append(f"stale sha512 entry: {name}")

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print(f"{apkbuild}: {len(sources)} sources and sha512 entries match")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
