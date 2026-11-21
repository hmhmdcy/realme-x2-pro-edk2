#!/usr/bin/env python3
"""Remove hand-appended package records that break apk-tools 3's DB parser.

`install-ncm-fallback.sh` used to append a record to
lib/apk/db/installed by hand:

    P:samurai-ncm-fallback
    V:1-r0
    A:noarch
            S:2048
            I:4096
    ...

apk-tools 3's apk_db_fdb_read() rejects that shape: the leading tab on S:/I:
and the A: field are not valid in the v3 installed-db grammar, and the whole
database then fails with "v2 database format error" - apk cannot install
anything afterwards.

The file that record described is already removed by
apply-rootfs-ncm-layer-fix.sh, so the record is pure residue: drop it.

Usage: repair-apkdb.py ROOT_TREE [--dry-run]
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path)
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()

    db = a.root / "lib/apk/db/installed"
    if not db.is_file():
        print(f"{db}: not found")
        return 1

    blocks = db.read_text().split("\n\n")
    kept = []
    removed = []
    for block in blocks:
        # A record can start with a checksum line (C:) rather than P:, so
        # match the package name anywhere in the block instead of only at
        # its first character.
        if "P:samurai-ncm-fallback\n" in block + "\n":
            removed.append(block)
            continue
        kept.append(block)

    if not removed:
        print("nothing to repair")
        return 0

    before = len(blocks)
    after = len(kept)
    text = "\n\n".join(kept)
    if not text.endswith("\n"):
        text += "\n"

    if a.dry_run:
        print(f"would remove {len(removed)} record(s), {before} -> {after} blocks")
        for block in removed:
            print(f"  {block.splitlines()[0]}")
        return 0

    db.write_text(text)
    print(f"removed {len(removed)} record(s), {before} -> {after} blocks")

    # Verify no unsupported field remains in this database.
    bad = re.findall(r"(?m)^\t(S|I):", text)
    if bad:
        print(f"warning: {len(bad)} tab-prefixed S:/I: lines remain", file=__import__("sys").stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
