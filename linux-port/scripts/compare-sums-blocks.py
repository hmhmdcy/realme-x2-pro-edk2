#!/usr/bin/env python3
"""Print the sha512sums block of two APKBUILDs and diff it line by line."""

from pathlib import Path
import re
import sys


def block(path: Path) -> list[str]:
    text = path.read_text()
    m = re.search(r'(?ms)^sha512sums="(.+?)"\n', text)
    if not m:
        raise SystemExit(f"{path}: no sha512sums block")
    return m.group(1).splitlines()


def main() -> int:
    a, b = Path(sys.argv[1]), Path(sys.argv[2])
    la, lb = block(a), block(b)
    print(f"{a}: {len(la)} lines")
    print(f"{b}: {len(lb)} lines")
    only_a = [l for l in la if l not in lb]
    only_b = [l for l in lb if l not in la]
    if only_a:
        print("only in", a.name)
        for line in only_a[:10]:
            parts = line.split()
            tail = parts[-1] if len(parts) >= 2 else "<blank or malformed>"
            print("  ", line[:40], "...", tail)
    if only_b:
        print("only in", b.name)
        for line in only_b[:10]:
            parts = line.split()
            tail = parts[-1] if len(parts) >= 2 else "<blank or malformed>"
            print("  ", line[:40], "...", tail)
    if not only_a and not only_b:
        print("blocks are identical")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
