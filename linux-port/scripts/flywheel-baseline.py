#!/usr/bin/env python3
"""Capture or compare a read-only baseline for the samurai debug flywheel."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import re
import subprocess

SCHEMA = "samurai-flywheel-baseline-v1"
ROOT = Path(__file__).resolve().parents[2]
LABEL = re.compile(r"^[A-Za-z0-9_.-]+$")


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_run(root, *arguments):
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *arguments],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if result.returncode:
        return ""
    return result.stdout.strip()


def git_state(root):
    return {
        "head": git_run(root, "rev-parse", "HEAD"),
        "branch": git_run(root, "branch", "--show-current"),
    }


def artifact_record(root, label, value):
    if not LABEL.fullmatch(label):
        raise ValueError(f"Invalid artifact label: {label}")
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = root / path
    path = path.resolve()
    if not path.is_file():
        raise ValueError(f"Artifact does not exist or is not a file: {value}")
    try:
        recorded_path = path.relative_to(root).as_posix()
    except ValueError:
        recorded_path = str(path)
    stat = path.stat()
    return {
        "path": recorded_path,
        "sha256": sha256(path),
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }


def artifacts(root, specs):
    records = {}
    for spec in specs:
        if "=" not in spec:
            raise ValueError(f"Expected LABEL=PATH, got: {spec}")
        label, value = spec.split("=", 1)
        if not label or not value:
            raise ValueError(f"Expected LABEL=PATH, got: {spec}")
        if label in records:
            raise ValueError(f"Duplicate artifact label: {label}")
        records[label] = artifact_record(root, label, value)
    if not records:
        raise ValueError("At least one --artifact LABEL=PATH is required")
    return records


def write_baseline(path, label, root, records, include_git):
    payload = {
        "schema": SCHEMA,
        "label": label,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "artifacts": records,
    }
    if include_git:
        payload["git"] = git_state(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def compare(baseline_path, root, current):
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    if baseline.get("schema") != SCHEMA:
        raise ValueError("Unsupported baseline schema")
    expected = baseline.get("artifacts")
    if not isinstance(expected, dict):
        raise ValueError("Baseline has no artifact map")

    problems = []
    for label in sorted(expected.keys() - current.keys()):
        problems.append(f"missing artifact: {label}")
    for label in sorted(current.keys() - expected.keys()):
        problems.append(f"new artifact: {label}")
    for label in sorted(expected.keys() & current.keys()):
        old = expected[label]
        new = current[label]
        if old.get("sha256") != new.get("sha256"):
            problems.append(
                f"changed artifact: {label} "
                f"{old.get('sha256')} -> {new.get('sha256')}"
            )
        elif old.get("size") != new.get("size"):
            problems.append(
                f"changed size: {label} "
                f"{old.get('size')} -> {new.get('size')}"
            )
        elif old.get("path") != new.get("path"):
            problems.append(
                f"moved artifact: {label} "
                f"{old.get('path')} -> {new.get('path')}"
            )

    if not problems:
        print(f"OK: {len(current)} artifacts match {baseline_path}")
        return 0
    for problem in problems:
        print(problem)
    return 1


def common_arguments(parser):
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--artifact",
        action="append",
        default=[],
        metavar="LABEL=PATH",
        help="artifact role and path; repeat for each file",
    )


parser = argparse.ArgumentParser(
    description="Capture or compare a read-only flywheel baseline."
)
subparsers = parser.add_subparsers(dest="command", required=True)

capture = subparsers.add_parser("capture", help="write a new baseline")
common_arguments(capture)
capture.add_argument("--out", required=True, type=Path)
capture.add_argument("--label", default="")
capture.add_argument("--git", action="store_true", help="record git HEAD/branch")

check = subparsers.add_parser("check", help="compare against a baseline")
common_arguments(check)
check.add_argument("baseline", type=Path)

args = parser.parse_args()

try:
    root = args.root.resolve()
    records = artifacts(root, args.artifact)
    if args.command == "capture":
        write_baseline(args.out, args.label, root, records, args.git)
        print(f"wrote {args.out} with {len(records)} artifacts")
        raise SystemExit(0)
    raise SystemExit(compare(args.baseline, root, records))
except (OSError, ValueError, json.JSONDecodeError) as error:
    print(f"error: {error}")
    raise SystemExit(2)
