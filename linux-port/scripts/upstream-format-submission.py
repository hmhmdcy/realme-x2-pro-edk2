#!/usr/bin/env python3
"""Normalise patch headers into submittable form.

The series mixes three header styles: full ``git format-patch`` headers,
plain ``Subject:`` lines without a ``From:``, and files with no author at
all.  Submitting any of those as-is gets the patch rejected by
``git send-email`` or by the list's own checks.

This tool rewrites only metadata, never the diff:

  * adds ``From:`` when missing,
  * normalises the subject to ``<subsystem prefix>: <description>``,
  * appends ``Signed-off-by`` when the author has no sign-off,
  * keeps an existing ``Signed-off-by`` chain untouched.

Usage:
    upstream-format-submission.py --patches DIR --author "Name <mail>" \
        --out DIR [--dry-run]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SUBJECT_RE = re.compile(r"^Subject:\s*(?:\[PATCH[^\]]*\]\s*)?(.+)$", re.M)
FROM_RE = re.compile(r"^From:\s*(.+)$", re.M)
SOB_RE = re.compile(r"^Signed-off-by:\s*(.+)$", re.M | re.I)
DATE_RE = re.compile(r"^Date:\s*(.+)$", re.M)

# Keep the subsystem prefixes the kernel expects for these files.
PREFIX_RULES = [
    (("drivers/tty/serial/",), "tty: serial"),
    (("drivers/i2c/",), "i2c"),
    (("drivers/input/",), "Input"),
    (("drivers/remoteproc/",), "remoteproc"),
    (("drivers/gpu/drm/panel/",), "drm/panel"),
    (("drivers/gpu/drm/msm/",), "drm/msm"),
    (("drivers/misc/",), "misc"),
    (("arch/arm64/boot/dts/",), "arm64: dts: qcom"),
    (("Documentation/devicetree/bindings/",),
     "dt-bindings"),
]


def desired_prefix(files: list[str]) -> str | None:
    for prefixes, prefix in PREFIX_RULES:
        if any(f.startswith(prefixes) for f in files):
            return prefix
    return None


def files_of(text: str) -> list[str]:
    out = []
    for line in text.splitlines():
        m = re.match(r"^\+\+\+ b/(\S+)", line)
        if m:
            out.append(m.group(1))
    return out


def format_one(text: str, author: str, dry: bool) -> tuple[str, list[str]]:
    notes = []
    files = files_of(text)
    prefix = desired_prefix(files)

    subject_match = SUBJECT_RE.search(text)
    subject = subject_match.group(1).strip() if subject_match else ""

    # A bare unified diff has no mail header at all.  git am needs a
    # usable Subject, so derive one from the file set and the first
    # changed symbol instead of leaving the commit message empty.
    if not subject:
        first_file = files[0] if files else "kernel"
        stem = Path(first_file).stem
        base = prefix or "misc"
        derived = f"{base}: adjust {stem}"
        notes.append(f"subject synthesised: {derived}")
        subject = derived
        header = (f"From: {author}\n"
                  f"Subject: {derived}\n\n")
        # Insert the header before the first diff line.
        lines = text.splitlines(keepends=True)
        first_diff = next((i for i, line in enumerate(lines)
                           if line.startswith(("diff --git", "--- a/"))), 0)
        text = "".join(lines[:first_diff]) + header + "".join(lines[first_diff:])
        subject_match = SUBJECT_RE.search(text)
    if prefix and subject and not subject.startswith(prefix):
        # Do not double-prefix a subject that already names another
        # subsystem: report instead of guessing.
        head = subject.split(":")[0]
        if any(z in head.lower() for z in ("dts", "drm", "tty", "i2c",
                                          "input", "remoteproc", "misc")):
            notes.append(f"subject keeps its own prefix: {subject}")
        else:
            notes.append(f"subject prefix added: {prefix}")
            text = SUBJECT_RE.sub(f"Subject: {prefix}: {subject}", text,
                                  count=1)

    if not FROM_RE.search(text):
        if subject_match:
            text = text[:subject_match.start()] + \
                f"From: {author}\n" + text[subject_match.start():]
        else:
            text = f"From: {author}\n" + text
        notes.append("From added")

    if not SOB_RE.search(text):
        body_end = text.rstrip() + "\n"
        if not body_end.endswith("---\n"):
            body_end += f"\nSigned-off-by: {author}\n"
        text = body_end
        notes.append("Signed-off-by added")

    return text, notes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--patches", type=Path, required=True)
    ap.add_argument("--author", default="")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not args.author:
        ap.error("--author is required for headers that lack a From line")

    if not args.dry_run:
        args.out.mkdir(parents=True, exist_ok=True)

    changed = 0
    for src in sorted(args.patches.glob("*.patch")):
        original = src.read_text(errors="replace")
        formatted, notes = format_one(original, args.author, args.dry_run)
        if notes:
            changed += 1
            print(f"{src.name}: " + "; ".join(notes))
        if not args.dry_run:
            (args.out / src.name).write_text(formatted)

    print()
    print(f"patches={len(list(args.patches.glob('*.patch')))} "
          f"normalised={changed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
