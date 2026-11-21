#!/usr/bin/env python3
"""Turn the patch audit into an actionable upstream plan.

The audit answers "what is this patch".  This tool answers "what do I do
with it, in what order, for which project".  It emits:

  * one directory per target project (linux, mesa),
  * inside each, one directory per work item with the patch copies and a
    README stating the upstream path and the blocking dependency,
  * a summary table printed to stdout and stored as plan.json.

Nothing is submitted anywhere: the output is a reviewable staging tree.

Usage:
    upstream-route.py --audit AUDIT_JSON --patches DIR --out DIR
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

PROJECT_RULES = {
    "mesa-upstream": ("mesa", "send to the Mesa merge-request flow; the "
                             "kernel series must not carry it"),
    "lkm-submit": ("linux/lkml", "generic subsystem change with no board "
                                "identifiers: normal subsystem review"),
    "own-series:dt": ("linux/dts", "device tree submission; needs the "
                                   "vendor-ABI split first"),
    "own-series:board-glue": ("linux/lkml", "subsystem change that names "
                                           "the board: submit after the DTS "
                                           "series is accepted"),
    "needs-rebase": ("linux/rebase", "patch no longer matches the tree; "
                                     "rebase it onto the pinned base before "
                                     "any review"),
    "split": ("linux/split", "mixed device and generic change; split before "
                              "review"),
    "drop": ("drop", "already present in the pinned tree; delete from the "
                      "series"),
}

ORDER = ["drop", "needs-rebase", "split", "own-series:dt",
         "own-series:board-glue", "lkm-submit", "mesa-upstream"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--audit", type=Path, required=True)
    ap.add_argument("--patches", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    audit = json.loads(args.audit.read_text())
    args.out.mkdir(parents=True, exist_ok=True)

    plan: list[dict] = []
    for rec in ORDER:
        items = [p for p in audit["patches"] if p["recommendation"] == rec]
        if not items:
            continue
        project, note = PROJECT_RULES[rec]
        work_dir = args.out / project
        work_dir.mkdir(parents=True, exist_ok=True)
        readme = work_dir / "README.md"
        lines = [f"# {project}", "", note, ""]
        for item in items:
            src = args.patches / item["file"]
            if src.is_file():
                shutil.copy2(src, work_dir / item["file"])
            lines += [f"## {item['file']}", "",
                      f"- subject: {item['subject'] or '(no Subject header)'}",
                      f"- state: {item['upstream_state']}",
                      f"- size: +{item['insertions']}/-{item['deletions']}",
                      f"- files: {len(item['files'])}"]
            for reason in item["rationale"]:
                lines.append(f"- {reason}")
            lines.append("")
            plan.append({"rec": rec, "project": project,
                         "file": item["file"],
                         "subject": item["subject"],
                         "files": item["files"],
                         "rationale": item["rationale"]})
        readme.write_text("\n".join(lines))

    print(f"{'item':<58} {'route':<16} action")
    print("-" * 100)
    for row in plan:
        print(f"{row['file'][:56]:<58} {row['project']:<16} {row['rec']}")

    counts: dict[str, int] = {}
    for row in plan:
        counts[row["rec"]] = counts.get(row["rec"], 0) + 1
    print()
    print("order:")
    for rec in ORDER:
        if rec in counts:
            print(f"  {ORDER.index(rec) + 1}. {rec}: {counts[rec]}")

    (args.out / "plan.json").write_text(json.dumps(
        {"order": ORDER, "counts": counts, "items": plan}, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
