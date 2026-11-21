#!/usr/bin/env python3
"""Rewrite an APKBUILD's sha512sums block to match source= order.

abuild's default_fetch() consumes two words of $sha512sums per entry of
$source, so the N-th checksum must belong to the N-th source.  Any insertion
that does not preserve that order makes every later file report
"sha512sum -c FAILED"; the message names the last file rather than the real
mismatch.  This script reorders (and de-duplicates) the block to follow
source= exactly, refusing to invent hashes for files without one.

Usage: normalize-apkbuild-sums.py APKBUILD
"""

from pathlib import Path
import re
import sys


def main() -> int:
    path = Path(sys.argv[1])
    text = path.read_text()
    m = re.search(r'(?ms)^sha512sums="(.+?)"\n', text)
    if not m:
        print(f"{path}: no sha512sums block", file=sys.stderr)
        return 1

    lines = [line for line in m.group(1).splitlines() if line.strip()]
    sums: dict[str, str] = {}
    for line in lines:
        parts = line.split()
        if len(parts) != 2 or not re.fullmatch(r"[0-9a-f]{128}", parts[0]):
            print(f"{path}: malformed line: {line[:60]}", file=sys.stderr)
            return 1
        sums[parts[1]] = parts[0]

    src_match = re.search(r'(?m)^source="(.+?)"\n', text, re.S)
    if not src_match:
        print(f"{path}: no source= block", file=sys.stderr)
        return 1
    sources = src_match.group(1).split()

    missing = [name for name in sources if name not in sums]
    if missing:
        print(f"{path}: no checksum for {missing}", file=sys.stderr)
        return 1

    ordered = [f"{sums[name]}  {name}" for name in sources]
    block = 'sha512sums="' + "\n".join(ordered) + '"\n'
    text = text[:m.start()] + block + text[m.end():]
    path.write_text(text)
    print(f"{path}: sha512sums reordered to {len(ordered)} source entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
