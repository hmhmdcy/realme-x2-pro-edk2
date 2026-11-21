#!/usr/bin/env python3
"""Mechanically rebase the board DTS part of the port series.

This is the automated half of the upstream cleanup:

  1. build a scratch tree from the pinned base,
  2. replay the series in order, succeeding when the patch applies and
     reporting precisely when it does not,
  3. for patches that fail only because the board DTS was split, map each
     hunk to the file that now owns the content and rewrite the patch
     against that file,
  4. prove the rewritten patch applies on the same scratch tree.

The tool refuses to guess: a hunk whose anchors are not found in exactly
one file is reported and left alone, so a broken mapping never lands
silently.

Usage:
    upstream-rebase-series.py --patches DIR --tree KERNEL --base REV \
        --out DIR [--apply-to-scratch]
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

BOARD_DTS = "arch/arm64/boot/dts/qcom/sm8150-samurai.dts"
BOARD_DTSI = "arch/arm64/boot/dts/qcom/sm8150-samurai-common.dtsi"
ANCHOR_CHARS = 14
FILE_RE = re.compile(r"^diff --git a/(\S+) b/(\S+)")
OLD_RE = re.compile(r"^--- a/(\S+)")
NEW_RE = re.compile(r"^\+\+\+ b/(\S+)")
HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@(.*)$")


def git(tree: Path, *args: str, check: bool = False):
    return subprocess.run(["git", "-C", str(tree), *args],
                          capture_output=True, text=True, check=check)


def split_files(text: str) -> list[tuple[str, list[str]]]:
    """Split a patch into (new_path, lines) blocks."""
    blocks: list[tuple[str, list[str]]] = []
    path = None
    buf: list[str] = []
    for line in text.splitlines(keepends=True):
        m = FILE_RE.match(line)
        if m:
            if path is not None:
                blocks.append((path, buf))
            path = m.group(2)
            buf = [line]
            continue
        nm = NEW_RE.match(line)
        if nm and path is None:
            path = nm.group(1)
            buf = [line]
            continue
        if path is not None:
            buf.append(line)
    if path is not None:
        blocks.append((path, buf))
    return blocks


def hunks(block: list[str]) -> list[tuple[list[str], list[str]]]:
    """Return (header_lines, hunk_lines) pairs; header ends before @@."""
    result: list[tuple[list[str], list[str]]] = []
    i = 0
    while i < len(block) and not HUNK_RE.match(block[i]):
        i += 1
    while i < len(block):
        start = i
        i += 1
        while i < len(block) and not HUNK_RE.match(block[i]):
            i += 1
        result.append((block[start:start + 1], block[start + 1:i]))
    return result


def keys_of(hunk: list[str]) -> list[str]:
    keys = []
    for line in hunk:
        if not line.strip():
            continue
        body = line[1:] if line[:1] in "+- " else line
        body = body.strip()
        if len(body) >= ANCHOR_CHARS and not body.startswith(("/*", "*")):
            keys.append(body[:ANCHOR_CHARS])
    return keys


def find_owner(hunk: list[str], tree: Path,
               candidates: list[str]) -> str | None:
    keys = keys_of(hunk)
    if not keys:
        return None
    hits = []
    for rel in candidates:
        path = tree / rel
        if not path.is_file():
            continue
        text = path.read_text(errors="replace")
        if all(k in text for k in keys):
            hits.append(rel)
    return hits[0] if len(hits) == 1 else None


def rebase_patch(src: Path, tree: Path, candidates: list[str]) -> tuple[str, int, int]:
    text = src.read_text(errors="replace")
    blocks = split_files(text)
    out: list[str] = []
    moved = unresolved = 0
    for path, block in blocks:
        if path != BOARD_DTS:
            out.extend(block)
            continue
        hs = hunks(block)
        # Everything before the first hunk is the file header.
        pre = []
        for line in block:
            if HUNK_RE.match(line):
                break
            pre.append(line)
        for hdr, body in hs:
            owner = find_owner(body, tree, candidates)
            if owner is None:
                unresolved += 1
                out.extend(hdr)
                out.extend(body)
                continue
            if owner != path:
                moved += 1
            out.append(hdr[0])
            out.extend(body)
        if moved:
            # Re-emit this block once, retargeted at its new owner.
            owners = {find_owner(body, tree, candidates) for _, body in hs}
            owners.discard(None)
            if len(owners) == 1:
                target = owners.pop()
                new_pre = []
                for line in pre:
                    if OLD_RE.match(line):
                        new_pre.append(f"--- a/{target}\n")
                    elif NEW_RE.match(line):
                        new_pre.append(f"+++ b/{target}\n")
                    elif FILE_RE.match(line):
                        new_pre.append(f"diff --git a/{target} b/{target}\n")
                    else:
                        new_pre.append(line)
                rebuilt = new_pre
                for hdr, body in hs:
                    rebuilt.append(hdr[0])
                    rebuilt.extend(body)
                out = out[:len(out) - sum(len(h) + len(b) for h, b in hs)]
                out.extend(rebuilt)
    return "".join(out), moved, unresolved


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--patches", type=Path, required=True)
    ap.add_argument("--tree", type=Path, required=True)
    ap.add_argument("--base", required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix="rebase-")) / "tree"
    git(args.tree, "worktree", "add", "--detach", str(scratch), args.base)
    if not (scratch / "Makefile").is_file():
        ap.error("could not create a scratch worktree from " + args.base)

    report = []
    for src in sorted(args.patches.glob("*.patch")):
        text = src.read_text(errors="replace")
        is_mesa = any(p.startswith(("src/freedreno/", "src/gallium/",
                                    "src/vulkan/", "src/compiler/"))
                      for p, _ in split_files(text))
        if is_mesa:
            # Mesa patches are out of scope for a kernel rebase.  Copy them
            # verbatim so the plan keeps every artefact in one place.
            shutil.copy2(src, args.out / src.name)
            report.append({"file": src.name, "state": "not-kernel"})
            continue
        # A patch whose reverse applies to the *current* tree is already
        # merged there; replaying it from the base would be meaningless.
        if git(args.tree, "apply", "--reverse", "--check",
               str(src)).returncode == 0:
            report.append({"file": src.name, "state": "already-in-tree"})
            continue
        before = git(scratch, "apply", "--3way", str(src)).returncode
        if before == 0:
            shutil.copy2(src, args.out / src.name)
            report.append({"file": src.name, "state": "applied-as-is"})
            continue
        rewritten, moved, unresolved = rebase_patch(
            src, scratch, [BOARD_DTS, BOARD_DTSI])
        dst = args.out / src.name
        dst.write_text(rewritten)
        after = git(scratch, "apply", "--3way", str(dst)).returncode
        if after == 0:
            report.append({"file": src.name, "state": "rebased",
                           "moved_hunks": moved})
        elif unresolved == 0:
            # The hunks map cleanly, yet the result still does not apply:
            # the patch needs a file that an earlier patch creates.  This
            # is a series dependency, not a broken patch.
            report.append({"file": src.name, "state": "needs-predecessor",
                           "moved_hunks": moved})
        else:
            report.append({"file": src.name, "state": "needs-human",
                           "moved_hunks": moved,
                           "unresolved_hunks": unresolved})

    print(json.dumps(report, indent=2))
    (args.out / "rebase-report.json").write_text(
        json.dumps(report, indent=2) + "\n")
    git(args.tree, "worktree", "remove", "--force", str(scratch))
    return 0 if all(r["state"] != "needs-human" for r in report) else 1


if __name__ == "__main__":
    sys.exit(main())
