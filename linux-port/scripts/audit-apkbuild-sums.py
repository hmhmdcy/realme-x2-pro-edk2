#!/usr/bin/env python3
"""Cross-check APKBUILD source= entries against its sha512sums block."""

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
    text = re.sub(
        r"\$\{(\w+)/([^/]*)/([^}]*)\}",
        lambda m: values.get(m.group(1), "").replace(m.group(2), m.group(3), 1),
        text,
    )
    text = re.sub(r"\$\{(\w+)\}", lambda m: values.get(m.group(1), ""), text)
    text = re.sub(
        r"\$(?=[A-Za-z_])[A-Za-z0-9_]+",
        lambda m: values.get(m.group(0)[1:], ""),
        text,
    )
    return text


def source_names(text: str) -> list[str]:
    m = re.search(r'(?m)^source="(.+?)"\n', expand_vars(text), re.S)
    if not m:
        return []
    return [Path(token.split("::", 1)[0]).name for token in m.group(1).split()]


def main() -> int:
    path = Path(sys.argv[1])
    text = path.read_text()
    src_match = re.search(r'(?m)^source="(.+?)"\n', text, re.S)
    sums_match = re.search(r'(?ms)^sha512sums="(.+?)"\n', text)
    if not src_match or not sums_match:
        print("missing source= or sha512sums= block", file=sys.stderr)
        return 1

    sources = source_names(text)
    raw_lines = sums_match.group(1).splitlines()
    lines = [line for line in raw_lines if line.strip()]
    names = []
    malformed = []
    for line in lines:
        parts = line.split()
        if len(parts) == 2 and re.fullmatch(r"[0-9a-f]{128}", parts[0]):
            names.append(parts[1])
        else:
            malformed.append(line[:60])

    print(f"sources={len(sources)} sum-lines={len(lines)} valid={len(names)}")
    if malformed:
        print("malformed lines:")
        for line in malformed:
            print(f"  {line}")
    missing = [s for s in sources if s not in names]
    extra = [n for n in names if n not in sources]
    if missing:
        print("missing sums:", missing)
    if extra:
        print("extra sums:", extra)
    dupes = {n: names.count(n) for n in set(names) if names.count(n) > 1}
    if dupes:
        print("duplicate sums:", dupes)
    ok = not (malformed or missing or extra or dupes)
    print("OK" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
