#!/usr/bin/env python3
"""Restore ownership and mode recorded in an APK database.

apk records the intended owner, group and mode of every installed file in
the `a:` field of /lib/apk/db/installed.  That contract matters for setuid
helpers such as /usr/libexec/dbus-daemon-launch-helper, which must stay
root:messagebus 4750 or D-Bus system service activation fails for every
client.

An image built by extracting a package tree into a staging directory can
lose that metadata when the extraction runs as root over a filesystem that
does not preserve group IDs (for example a root-owned chown of the whole
tree).  The package database still holds the truth, so re-applying it is
a standard repair rather than a board-specific workaround.

Usage:
    repair-installed-ownership.py --root / [--check]
"""

from __future__ import annotations

import argparse
import os
import stat
import sys
from pathlib import Path


def install_records(text: str):
    """Yield (path, owner, group, mode) for records that carry an a: field."""
    for block in text.split("\n\n"):
        directory = ""
        path = ""
        for line in block.splitlines():
            key, _, value = line.partition(":")
            if key == "F":
                directory = value
            elif key == "R":
                path = (value if value.startswith("/")
                        else f"{directory}/{value}")
            elif key == "a":
                if not path:
                    continue
                parts = value.split(":")
                if len(parts) != 3:
                    continue
                try:
                    # apk stores uid/gid in decimal and the mode in octal.
                    uid, gid, mode = int(parts[0]), int(parts[1]), int(parts[2], 8)
                except ValueError:
                    continue
                yield path, uid, gid, mode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("/"))
    parser.add_argument("--check", action="store_true",
                        help="report mismatches instead of repairing them")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    root = args.root
    database = root / "lib/apk/db/installed"
    if not database.is_file():
        raise SystemExit(f"missing apk database: {database}")
    if not args.check and os.geteuid() != 0:
        raise SystemExit("repair requires root")

    mismatches: list[str] = []
    repaired = 0
    scanned = 0
    for relative, uid, gid, mode in install_records(
            database.read_text(errors="replace")):
        target = root / relative.lstrip("/")
        if not target.exists() and not target.is_symlink():
            continue
        if target.is_symlink():
            continue
        scanned += 1
        st = target.lstat()
        want = (uid, gid, mode)
        have = (st.st_uid, st.st_gid, stat.S_IMODE(st.st_mode))
        if have == want:
            continue
        mismatches.append(
            f"{'/' + relative}: {have[0]}:{have[1]} {have[2]:04o}"
            f" -> {want[0]}:{want[1]} {want[2]:04o}")
        if args.check:
            continue
        os.chown(target, uid, gid)
        os.chmod(target, mode)
        repaired += 1
        if args.verbose:
            print(mismatches[-1])

    print(f"root: {root}")
    print(f"files with apk ownership metadata: {scanned}")
    print(f"mismatches: {len(mismatches)}")
    if args.check:
        for item in mismatches:
            print(f"  MISMATCH {item}")
        return 1 if mismatches else 0
    print(f"repaired: {repaired}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
