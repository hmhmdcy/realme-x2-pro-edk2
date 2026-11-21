#!/usr/bin/env python3
"""Check that sha512sums lines align positionally with source= entries.

abuild's default_fetch() consumes two words of $sha512sums per $source entry,
so the N-th checksum must belong to the N-th source.  A single out-of-order
line makes every following file report FAILED, while the first mismatch is
the real defect.

Usage: check-sum-order.py APKBUILD
"""

from pathlib import Path
import re
import sys


def main() -> int:
    path = Path(sys.argv[1])
    text = path.read_text()
    src = re.search(r'(?m)^source="(.+?)"\n', text, re.S)
    sums = re.search(r'(?ms)^sha512sums="(.+?)"\n', text)
    if not src or not sums:
        print("missing source= or sha512sums=", file=sys.stderr)
        return 1

    sources = src.group(1).split()
    lines = [l for l in sums.group(1).splitlines() if l.strip()]
    if len(lines) != len(sources):
        print(f"count mismatch: {len(lines)} sums vs {len(sources)} sources")
        return 1

    misordered = []
    for index, (line, source) in enumerate(zip(lines, sources), start=1):
        parts = line.split()
        if len(parts) != 2:
            misordered.append((index, "<malformed>", source))
            continue
        if parts[1] != source:
            misordered.append((index, parts[1], source))

    if misordered:
        for index, have, want in misordered:
            print(f"position {index}: sha512sums has {have!r}, source has {want!r}")
        print(f"FAIL: {len(misordered)} misordered entr(ies)")
        return 1
    print(f"OK: {len(sources)} entries are positionally aligned")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
