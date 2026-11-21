#!/usr/bin/env python3
"""Verify every sha512sums entry in an APKBUILD against the source files.

Checks only source integrity and coverage (no network, no buildroot), so it
catches the "added a file to source= but forgot the checksum" and
"edited a helper script without refreshing sha512sums" classes of error that
make abuild reject the package.

Usage: verify-apkbuild-sources.py APKBUILD
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path


def expand_vars(text: str) -> str:
    values: dict[str, str] = {}
    for name, value in re.findall(r"(?m)^(\w+)=(.*)$", text):
        value = value.strip()
        if value[:1] == '"':
            value = value[1:].split('"', 1)[0]
        values[name] = value

    # APKBUILD supports shell-style ${var/old/new}; phoc uses it to turn
    # 0.57.0 into the released tarball name phoc-0.57.tar.xz.
    text = re.sub(
        r"\$\{(\w+)/([^/]*)/([^}]*)\}",
        lambda m: values.get(m.group(1), "").replace(m.group(2), m.group(3), 1),
        text,
    )
    text = re.sub(
        r"\$\{(\w+)\}",
        lambda m: values.get(m.group(1), ""),
        text,
    )
    text = re.sub(
        r"\$(?=[A-Za-z_])[A-Za-z0-9_]+",
        lambda m: values.get(m.group(0)[1:], ""),
        text,
    )
    return text


def parse_sources(text: str) -> list[str]:
    m = re.search(r'(?m)^source="(.+?)"\n', text, re.S)
    if not m:
        return []
    names = []
    source_text = expand_vars(text)
    source_match = re.search(r'(?m)^source="(.+?)"\n', source_text, re.S)
    if source_match:
        for token in source_match.group(1).split():
            # For name::url, the local name is the part before "::".
            local = token.split("::", 1)[0]
            names.append(Path(local).name)
    return names


def parse_sums(text: str) -> dict[str, str]:
    m = re.search(r'(?m)^sha512sums="(.+?)"\n', text, re.S)
    if not m:
        return {}
    sums: dict[str, str] = {}
    for line in m.group(1).splitlines():
        parts = line.split()
        if len(parts) == 2 and re.fullmatch(r"[0-9a-f]{128}", parts[0]):
            sums[parts[1]] = parts[0]
    return sums


def main() -> int:
    apkbuild = Path(sys.argv[1])
    srcdir = apkbuild.parent
    text = apkbuild.read_text()
    sources = parse_sources(text)
    sums = parse_sums(text)

    problems: list[str] = []
    checked = 0
    for name in sources:
        # Files fetched from a URL are not present locally; only verify the
        # ones that are shipped next to the APKBUILD.
        path = srcdir / name
        if not path.is_file():
            if name not in sums:
                problems.append(f"missing checksum for remote source {name}")
            continue
        digest = hashlib.sha512(path.read_bytes()).hexdigest()
        if name not in sums:
            problems.append(f"no sha512sums entry for {name}")
        elif sums[name] != digest:
            problems.append(f"checksum mismatch for {name}")
        else:
            checked += 1

    for name in sums:
        if name not in sources:
            problems.append(f"sha512sums entry without source: {name}")

    print(f"{apkbuild}: {len(sources)} sources, {checked} local files verified")
    if problems:
        for p in problems:
            print(f"FAIL {p}", file=sys.stderr)
        return 1
    print("OK: every local source matches its sha512 entry")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
