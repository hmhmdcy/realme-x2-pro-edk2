#!/usr/bin/env python3
"""Turn the flat port patch directory into reviewable upstream series.

The port grew one patch per problem, including board overrides, generic
driver fixes and vendor-only configuration in the same numbered list.
Upstream workflows reject that shape: a device submission is one series,
a subsystem fix is another, and a board-private tweak is neither.

This tool reads the classification produced by
``upstream-patch-audit.py`` and, for every patch that mixes a board
change with a generic one, emits two standalone patches:

    <prefix>-board.patch   only files under arch/arm64/boot/dts/ or with
                           board identifiers
    <prefix>-generic.patch everything else

It never touches git history and never rewrites the source tree, so it
is safe to run while the phone is offline.

Usage:
    upstream-split-series.py --patches DIR --audit AUDIT_JSON --out DIR
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

BOARD_TOKENS = ("samurai", "realme", "rmx1931", "sofef03f", "s3706",
                "bq28z610", "s5kgw1", "s5k3m5", "imx319", "imx471")
DTS_PREFIX = "arch/arm64/boot/dts/"
FILE_LINE = re.compile(r"^diff --git a/(\S+) b/(\S+)")
HUNK_LINE = re.compile(r"^(diff --git|index |new file|deleted file|"
                       r"similarity|rename |--- a/|\+\+\+ b/|@@ )")


def is_board_file(path: str) -> bool:
    if path.startswith(DTS_PREFIX):
        return True
    return any(tok in path.lower() for tok in BOARD_TOKENS)


def split_patch(text: str) -> tuple[str, str]:
    """Return (header, body) where header ends right before the first hunk."""
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.startswith(("diff --git", "--- a/", "Index: ")):
            return "".join(lines[:i]), "".join(lines[i:])
    return text, ""


def group_hunks(body: str) -> list[tuple[str, list[str]]]:
    """Group the file diffs so each group can be written out independently."""
    groups: list[tuple[str, list[str]]] = []
    current_path = None
    current: list[str] = []
    for line in body.splitlines(keepends=True):
        m = FILE_LINE.match(line)
        if m:
            if current_path is not None:
                groups.append((current_path, current))
            current_path = m.group(2)
            current = [line]
            continue
        if line.startswith("--- a/"):
            # A bare unified diff starts a new file with the --- line.
            # Flush the previous group unless this --- belongs to the
            # diff header that already opened current.
            if current_path is not None and not any(
                    previous.startswith(("diff --git", "--- a/"))
                    for previous in current[:1]):
                groups.append((current_path, current))
                current_path = None
                current = []
            if current_path is None:
                current_path = line[len("--- a/"):].strip()
                current = [line]
            else:
                current.append(line)
            continue
        if line.startswith("+++ b/") and current_path is None:
            current_path = line[len("+++ b/"):].strip()
            current = [line]
            continue
        if current_path is not None:
            current.append(line)
    if current_path is not None:
        groups.append((current_path, current))
    return groups


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--patches", type=Path, required=True)
    ap.add_argument("--audit", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    audit = json.loads(args.audit.read_text())
    by_file = {p["file"]: p for p in audit["patches"]}
    args.out.mkdir(parents=True, exist_ok=True)

    written: dict[str, list[str]] = {"drop": [], "split": [], "keep": []}
    for path in sorted(args.patches.glob("*.patch")):
        facts = by_file.get(path.name)
        if facts is None:
            continue
        rec = facts["recommendation"]
        if rec == "drop":
            written["drop"].append(path.name)
            continue
        if rec != "split":
            written["keep"].append(path.name)
            continue

        text = path.read_text()
        header, body = split_patch(text)
        groups = group_hunks(body)
        board = [(p, h) for p, h in groups if is_board_file(p)]
        generic = [(p, h) for p, h in groups if not is_board_file(p)]
        if not board or not generic:
            written["keep"].append(path.name)
            continue

        stem = path.stem
        for suffix, parts in (("board", board), ("generic", generic)):
            out = args.out / f"{stem}-{suffix}.patch"
            out.write_text(header + "".join(
                line for _, hunk in parts for line in hunk))
            written["split"].append(out.name)

        cover = args.out / f"{stem}-SPLIT.md"
        cover.write_text(
            f"# Split of `{path.name}`\n\n"
            f"Subject: {facts['subject']}\n\n"
            "Upstream wants the device description and the generic driver\n"
            "change reviewed separately, so this file was split into:\n\n"
            f"- `{stem}-board.patch` ({len(board)} board file(s)): device\n"
            "  submission, depends on the vendor-ABI split and the board\n"
            "  maintainers' review.\n"
            f"- `{stem}-generic.patch` ({len(generic)} generic file(s)):\n"
            "  subsystem submission, reviewable without the device tree.\n\n"
            "Board files:\n"
            + "".join(f"- `{p}`\n" for p, _ in board)
            + "\nGeneric files:\n"
            + "".join(f"- `{p}`\n" for p, _ in generic))

    print(json.dumps({
        "dropped_duplicates": written["drop"],
        "split_into": written["split"],
        "kept_as_is": len(written["keep"]),
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
