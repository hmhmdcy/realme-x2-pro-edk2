#!/usr/bin/env python3
"""Classify every local kernel patch against the pinned upstream tree.

The port carries a patch series that mixes three very different kinds of
change.  They cannot follow the same upstream path, so this tool separates
them and reports, per patch, what the evidence says:

  upstream-covered   the change (or its equivalent) is already in the
                     pinned upstream tree; the patch is dead weight and
                     should be dropped from the series
  generic-submittable touches only generic kernel files, no board or
                     device identifiers; candidate for LKML review
  vendor-overlay     adds a board DTS/DTSI or generic driver hooks that
                     are board-specific; needs its own upstream submission
                     or must stay in the port tree
  board-private      named after the handset, encodes hardware wiring or
                     calibration; stays out of upstream

Usage:
    upstream-patch-audit.py --patches DIR --tree KERNEL_TREE [--json OUT]

Exit code 1 when a patch is reported as upstream-covered, so the series
can be trimmed in CI instead of silently carrying duplicates.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path

HEADER_RE = re.compile(r"^(Subject|From|Date):\s*(.*)$")
DIFF_RE = re.compile(r"^diff --git a/(\S+) b/(\S+)")
# Some patches in this series were hand-edited and lost the "diff --git"
# line, so fall back to the ---/+++ pair.
PLUS_RE = re.compile(r"^\+\+\+ b/(\S+)")
MINUS_RE = re.compile(r"^--- a/(\S+)")
BOARD_TOKENS = ("samurai", "realme", "rmx1931", "sofef03f", "s3706",
                "bq28z610", "s5kgw1", "s5k3m5", "imx319", "imx471")
GENERIC_PREFIXES = ("drivers/", "sound/", "net/", "include/", "fs/",
                    "kernel/", "lib/", "mm/", "block/", "security/")
DTS_PREFIXES = ("arch/arm64/boot/dts/",)


@dataclass
class PatchFacts:
    file: str
    subject: str
    author: str
    upstream_state: str
    files: list[str] = field(default_factory=list)
    touches_board: bool = False
    touches_dts: bool = False
    insertions: int = 0
    deletions: int = 0
    recommendation: str = ""
    rationale: list[str] = field(default_factory=list)


def read_header(path: Path) -> tuple[str, str, str]:
    subject = author = ""
    for line in path.read_text(errors="replace").splitlines():
        if not line.strip():
            break
        m = HEADER_RE.match(line)
        if not m:
            continue
        key, value = m.group(1), m.group(2).strip()
        if key == "Subject":
            subject = re.sub(r"^\[PATCH[^\]]*\]\s*", "", value)
        elif key == "From":
            author = value
    return subject, author, ""


def collect_files(path: Path) -> tuple[list[str], int, int]:
    files: list[str] = []
    insertions = deletions = 0
    for line in path.read_text(errors="replace").splitlines():
        m = DIFF_RE.match(line)
        if m:
            files.append(m.group(2))
            continue
        m = PLUS_RE.match(line)
        if m:
            files.append(m.group(1))
            continue
        elif line.startswith("+") and not line.startswith("+++"):
            insertions += 1
        elif line.startswith("-") and not line.startswith("---"):
            deletions += 1
    return files, insertions, deletions


def find_commit(tree: Path, subject: str) -> str | None:
    if not subject:
        return None
    try:
        out = subprocess.run(
            ["git", "-C", str(tree), "log", "--all", "--oneline",
             "--grep", subject, "-F", "--max-count=1"],
            capture_output=True, text=True, check=False)
    except OSError:
        return None
    text = out.stdout.strip()
    return text or None


def patch_state(tree: Path, patch: Path) -> str:
    """Decide whether the pinned tree already holds this change.

    Subject matching is useless here because the port history was
    squashed, so ask git instead: a patch that reverses cleanly is
    already applied, while one that applies cleanly is a live delta.
    """

    def run(*args: str) -> int:
        return subprocess.run(["git", "-C", str(tree), "apply", *args,
                               str(patch)],
                              capture_output=True, check=False).returncode

    if run("--reverse", "--check") == 0:
        return "already-applied"
    if run("--check") == 0:
        return "applies-clean"
    return "conflict"


def sequence_state(tree: Path, patches: list[Path]) -> dict[str, str]:
    """Replay the series in order on a scratch copy of the tree.

    A neat per-patch "git apply --check" against the final tree lies in
    both directions: later patches assume earlier ones landed, and a
    patch written against a squashed file will never match the split
    file.  Replaying the whole series answers the question upstream
    actually asks: is this series self-consistent on the pinned base?
    """
    import shutil
    import tempfile

    result: dict[str, str] = {}
    with tempfile.TemporaryDirectory() as tmp:
        scratch = Path(tmp) / "tree"
        base = subprocess.run(
            ["git", "-C", str(tree), "rev-list", "--max-parents=0",
             "HEAD"], capture_output=True, text=True, check=False)
        roots = base.stdout.split()
        if not roots:
            return result
        subprocess.run(["git", "-C", str(tree), "worktree", "add", "--detach",
                        str(scratch), roots[0]], capture_output=True,
                       check=False)
        if not (scratch / "Makefile").is_file():
            return result
        for patch in patches:
            applied = subprocess.run(
                ["git", "-C", str(scratch), "apply", "--3way", str(patch)],
                capture_output=True, check=False).returncode == 0
            result[patch.name] = "replay-ok" if applied else "replay-fail"
        subprocess.run(["git", "-C", str(tree), "worktree", "remove",
                        "--force", str(scratch)], capture_output=True,
                       check=False)
    return result


def has_board_tokens(subject: str, files: list[str], body: str) -> bool:
    haystack = " ".join([subject, *files]).lower()
    if any(tok in haystack for tok in BOARD_TOKENS):
        return True
    return "/samurai" in body.lower() or "qcom,board-id" in body.lower()


def classify(path: Path, tree: Path, replay: dict[str, str]) -> PatchFacts:
    subject, author, _ = read_header(path)
    files, ins, dels = collect_files(path)
    body = path.read_text(errors="replace")
    state = patch_state(tree, path)
    replay_state = replay.get(path.name, "")
    commit = find_commit(tree, subject)
    facts = PatchFacts(
        file=path.name,
        subject=subject,
        author=author,
        upstream_state="unknown",
        files=files,
        insertions=ins,
        deletions=dels,
    )
    facts.touches_dts = any(f.startswith(DTS_PREFIXES) for f in files)
    facts.touches_board = has_board_tokens(subject, files, body)

    # Mesa changes cannot be judged against a kernel checkout: replaying
    # them there always fails and would hide the real target project.
    project = "mesa" if any(
        f.startswith(("src/freedreno/", "src/gallium/", "src/vulkan/",
                      "src/compiler/")) for f in files) else "linux"

    if project == "mesa":
        facts.upstream_state = "not-upstream"
        facts.recommendation = "mesa-upstream"
        facts.rationale.append(
            "Mesa/Turnip source: goes to mesa's merge-request flow, tracked "
            "by the mesa package recipe rather than the kernel series")
        return facts

    if state == "already-applied":
        facts.upstream_state = "in-tree"
        facts.recommendation = "drop"
        facts.rationale.append(
            "patch reverses against the pinned tree: the change is already "
            "there, so the series only carries a duplicate")
        return facts

    facts.upstream_state = state
    if replay_state == "replay-fail":
        facts.recommendation = "needs-rebase"
        facts.rationale.append(
            "does not survive a sequential replay on the pinned base: the "
            "patch was written against an earlier tree shape, so it must be "
            "rebased in place before it can be submitted")
        return facts
    if commit:
        facts.rationale.append("matching subject in history: "
                               + commit.split()[0])

    if facts.touches_board:
        board_files = [f for f in files
                       if f.startswith(DTS_PREFIXES)
                       or any(tok in f.lower() for tok in BOARD_TOKENS)]
        generic_files = [f for f in files if f not in board_files]
        if generic_files and board_files:
            facts.recommendation = "split"
            facts.rationale.append(
                "mixed change: board files "
                f"({len(board_files)}) and generic files "
                f"({len(generic_files)}) in one patch; split into a device "
                "overlay plus a generic driver submission")
        elif facts.touches_dts:
            facts.recommendation = "own-series:dt"
            facts.rationale.append(
                "board DTS change: needs a dedicated device submission "
                "with the vendor-ABI split, not a generic driver series")
        else:
            facts.recommendation = "own-series:board-glue"
            facts.rationale.append(
                "board-identified driver/subsystem change: submit after "
                "the DTS lands, or keep in the port tree")
        return facts

    generic = any(f.startswith(GENERIC_PREFIXES) for f in files)
    if generic:
        facts.upstream_state = "not-upstream"
        facts.recommendation = "lkm-submit"
        facts.rationale.append(
            "generic subsystem file with no board identifiers")
        return facts

    facts.upstream_state = "not-upstream"
    facts.recommendation = "review"
    facts.rationale.append("unclassified path set; inspect by hand")
    return facts


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--patches", type=Path, required=True)
    ap.add_argument("--tree", type=Path, required=True,
                    help="pinned upstream kernel checkout")
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()

    if not (args.tree / "Makefile").is_file():
        ap.error("--tree must point at a kernel checkout")

    patches = sorted(p for p in args.patches.iterdir()
                     if p.suffix == ".patch")
    replay = sequence_state(args.tree, patches)
    facts = [classify(p, args.tree, replay) for p in patches]

    grouped: dict[str, list[str]] = {}
    for f in facts:
        grouped.setdefault(f.recommendation, []).append(f.file)

    for rec in sorted(grouped):
        print(f"== {rec} ({len(grouped[rec])})")
        for name in grouped[rec]:
            f = next(x for x in facts if x.file == name)
            print(f"  {name}")
            print(f"    {f.subject}")
            print(f"    state: {f.upstream_state}  "
                  f"+{f.insertions}/-{f.deletions}  files={len(f.files)}")
            for line in f.rationale:
                print(f"    - {line}")

    dropped = [f.file for f in facts if f.recommendation == "drop"]
    print()
    print(f"patches={len(facts)} droppable={len(dropped)}")
    if dropped:
        print("series still carries changes already in the pinned tree: "
              + ", ".join(dropped))

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(
            {"tree": str(args.tree), "patches": [asdict(f) for f in facts]},
            indent=2) + "\n")

    return 1 if dropped else 0


if __name__ == "__main__":
    sys.exit(main())
