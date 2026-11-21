#!/usr/bin/env python3
"""Validate an apk-tools v3 `lib/apk/db/installed` file.

Mirrors the state machine in apk-tools 3 src/database.c (apk_db_fdb_read):

- a line must be at least 2 chars with ':' in position 1;
- after 'F'<dir>, the following entries must be 'M' or 'a' (dir acl) or
  'R'<file> / 'a' (file acl) / 'Z' (digest);
- 'R' (file) requires a preceding 'F' (diri);
- 'Z' requires a preceding 'R' (file);
- 'a'/'M' require a preceding F or R.

Any violation makes apk reject the whole database with
"v2 database format error", which is what the device reports.

Usage: validate-apkdb.py ROOT_TREE   (or pass the installed file directly)
"""

from __future__ import annotations

import sys
from pathlib import Path


def resolve(argv: str) -> Path:
    p = Path(argv)
    if p.is_dir():
        p = p / "lib/apk/db/installed"
    return p


def main() -> int:
    db = resolve(sys.argv[1])
    if not db.is_file():
        print(f"{db}: not found", file=sys.stderr)
        return 1

    problems: list[str] = []
    pkg = None
    diri = None
    file = None
    lineno = 0
    packages = 0

    for raw in db.read_text().splitlines():
        lineno += 1
        if len(raw) < 2:
            # Blank between records: commit and reset.
            if pkg:
                packages += 1
            pkg = None
            diri = None
            file = None
            continue
        if raw[1] != ":":
            problems.append(f"line {lineno}: no colon in field: {raw[:40]!r}")
            continue
        field, value = raw[0], raw[2:]

        if field == "P":
            pkg = value
            diri = None
            file = None
        elif field == "F":
            if pkg is None:
                problems.append(f"line {lineno}: F before any P")
            diri = value
            file = None
        elif field == "R":
            if diri is None:
                problems.append(f"line {lineno}: R {value!r} without preceding F")
            file = value
        elif field == "Z":
            if file is None:
                problems.append(f"line {lineno}: Z without preceding R")
        elif field in ("a", "M"):
            if file is None and diri is None:
                problems.append(f"line {lineno}: {field} without F or R")
            parts = value.split(":")
            if len(parts) < 3 or not all(p.isdigit() for p in parts[:3]):
                problems.append(f"line {lineno}: bad acl {value!r}")
        elif field == "C":
            if pkg is not None:
                problems.append(f"line {lineno}: C after P within one record")

    if pkg:
        packages += 1

    print(f"{db}: {lineno} lines, {packages} records")
    if problems:
        for problem in problems[:20]:
            print(f"FAIL {problem}", file=sys.stderr)
        if len(problems) > 20:
            print(f"... {len(problems) - 20} more", file=sys.stderr)
        return 1
    print("OK: database passes the v3 field-state checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
