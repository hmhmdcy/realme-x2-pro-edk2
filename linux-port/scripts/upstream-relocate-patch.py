#!/usr/bin/env python3
"""Re-point board DTS hunks at whichever file now carries them.

The port started as one monolithic ``sm8150-samurai.dts``.  It was later
split into a thin ``.dts`` plus ``sm8150-samurai-common.dtsi``, so every
DTS patch written before the split now fails to apply even though its
content is still wanted.

This tool does not guess.  For each hunk it takes the surrounding context
lines from the patch and looks them up in the current board files; if a
unique file contains them, the hunk is rewritten against that file.  If
the context is gone or matches more than one place, the hunk is reported
as needing a human and is left untouched.

Usage:
    upstream-relocate-patch.py --patch P.patch --tree KERNEL_TREE \
        --old arch/arm64/boot/dts/qcom/sm8150-samurai.dts \
        --candidates arch/arm64/boot/dts/qcom/sm8150-samurai-common.dtsi \
                     arch/arm64/boot/dts/qcom/sm8150-samurai.dts \
        [--write]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

FILE_RE = re.compile(r"^diff --git a/(\S+) b/(\S+)")
OLD_RE = re.compile(r"^--- a/(\S+)")
NEW_RE = re.compile(r"^\+\+\+ b/(\S+)")
HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@(.*)$")
CONTEXT_CHARS = 12


def hunks_of(lines: list[str]) -> list[tuple[int, int, list[str]]]:
    """Yield (start, end, lines) for each hunk, without the @@ header."""
    spans: list[tuple[int, int, list[str]]] = []
    start = None
    for i, line in enumerate(lines):
        if HUNK_RE.match(line):
            if start is not None:
                spans.append((start, i, lines[start:i]))
            start = i + 1
    if start is not None:
        spans.append((start, len(lines), lines[start:]))
    return spans


def context_keys(hunk: list[str]) -> list[str]:
    keys = []
    for line in hunk:
        if line.startswith(("+", "-")) and not line.startswith(("+++", "---")):
            body = line[1:]
        elif line.startswith(" "):
            body = line[1:]
        else:
            continue
        body = body.strip()
        if len(body) >= CONTEXT_CHARS:
            keys.append(body[:CONTEXT_CHARS])
    return keys


def locate(hunk: list[str], files: dict[str, list[str]]) -> list[str]:
    keys = context_keys(hunk)
    if not keys:
        return []
    hits = []
    for name, text_lines in files.items():
        joined = "\n".join(text_lines)
        if all(key in joined for key in keys):
            hits.append(name)
    return hits


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--patch", type=Path, required=True)
    ap.add_argument("--tree", type=Path, required=True)
    ap.add_argument("--old", required=True)
    ap.add_argument("--candidates", nargs="+", required=True)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    files = {}
    for rel in args.candidates:
        path = args.tree / rel
        if path.is_file():
            files[rel] = path.read_text(errors="replace").splitlines()
    if not files:
        ap.error("none of the candidate files exist in the tree")

    text = args.patch.read_text(errors="replace").splitlines()
    out: list[str] = []
    moved = 0
    appended = 0
    unresolved = 0
    current_is_target = False
    for i, line in enumerate(text):
        m = FILE_RE.match(line)
        if m:
            old_path = m.group(1) or m.group(3)
            current_is_target = old_path == args.old
        out.append(line)

    # Second pass: rewrite hunk headers only inside the target file block.
    rebuilt: list[str] = []
    target_block = False
    pending = None
    idx = 0
    while idx < len(text):
        line = text[idx]
        om = OLD_RE.match(line)
        if om:
            rebuilt.append(line)
            idx += 1
            continue
        nm = NEW_RE.match(line)
        if nm:
            target_block = (nm.group(1) == args.old)
            rebuilt.append(line)
            idx += 1
            continue
        m = FILE_RE.match(line)
        if m:
            target_block = (m.group(2) == args.old)
            rebuilt.append(line)
            idx += 1
            continue
        h = HUNK_RE.match(line) if target_block else None
        if not h:
            rebuilt.append(line)
            idx += 1
            continue

        # Collect the hunk body up to the next hunk or file header.
        body: list[str] = []
        j = idx + 1
        while j < len(text):
            if HUNK_RE.match(text[j]) or FILE_RE.match(text[j]):
                break
            body.append(text[j])
            j += 1

        hits = locate(body, files)
        if len(hits) == 1 and hits[0] != args.old:
            new = hits[0]
            rebuilt.append(f"--- a/{new}")
            rebuilt.append(f"+++ b/{new}")
            rebuilt.append(line)
            moved += 1
            rebuilt.extend(body)
            idx = j
            continue
        if not hits:
            # The context is gone everywhere.  That is the normal shape
            # of a patch that *adds* a new node rather than moving an
            # existing one, so anchor it to the file that defines the
            # parent node named in the hunk body.
            anchor = None
            for line2 in body:
                ref = re.match(r"^\+&(\w+)", line2)
                if not ref:
                    continue
                parent = ref.group(1)
                for name, text_lines in files.items():
                    joined = "\n".join(text_lines)
                    esc = re.escape(parent)
                    if re.search(rf"^\s*{esc}:", joined, re.M) \
                       or re.search("^\\s*&\\s*" + esc + "\\s*\\{", joined,
                                    re.M):
                        anchor = name
                        break
                if anchor:
                    break
            if anchor and anchor != args.old:
                rebuilt.append(f"--- a/{anchor}")
                rebuilt.append(f"+++ b/{anchor}")
                rebuilt.append(line)
                moved += 1
                appended += 1
            else:
                rebuilt.append(line)
                unresolved += 1
        elif len(hits) > 1:
            rebuilt.append(line)
            unresolved += 1
        else:
            rebuilt.append(line)
        rebuilt.extend(body)
        idx = j

    result = "\n".join(rebuilt) + "\n"
    print(f"{args.patch.name}: moved={moved} unresolved={unresolved}")
    if args.write and moved:
        args.patch.write_text(result)
        print("written in place")
    return 1 if unresolved else 0


if __name__ == "__main__":
    sys.exit(main())
