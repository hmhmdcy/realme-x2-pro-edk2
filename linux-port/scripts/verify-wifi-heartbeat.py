#!/usr/bin/env python3
"""Validate a monotonic SSH heartbeat collected over Wi-Fi."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("log", type=Path)
    parser.add_argument("--min-samples", type=int, default=1800)
    parser.add_argument("--min-seconds", type=float, default=1790)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    failures: list[str] = []
    rows: list[tuple[int, float]] = []
    exit_code: int | None = None
    for line in args.log.read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if line.startswith("START_UTC=") or line.startswith("END_UTC="):
            continue
        if fields and fields[0].startswith("EXIT="):
            try:
                exit_code = int(fields[0].split("=", 1)[1])
            except ValueError:
                failures.append("invalid EXIT line")
            continue
        if len(fields) != 2:
            failures.append(f"unparseable line: {line!r}")
            continue
        try:
            rows.append((int(fields[0]), float(fields[1])))
        except ValueError:
            failures.append(f"non-numeric sample: {line!r}")

    if exit_code != 0:
        failures.append(f"SSH process exit code: {exit_code}")
    if len(rows) < args.min_samples:
        failures.append(f"short heartbeat: {len(rows)} < {args.min_samples}")
    if rows:
        epoch_delta = rows[-1][0] - rows[0][0]
        uptime_delta = rows[-1][1] - rows[0][1]
        if epoch_delta < args.min_seconds:
            failures.append(f"short epoch span: {epoch_delta}")
        if uptime_delta < args.min_seconds:
            failures.append(f"short uptime span: {uptime_delta}")
        gaps = [
            rows[index][1] - rows[index - 1][1]
            for index in range(1, len(rows))
        ]
        if any(gap <= 0 or gap > 5 for gap in gaps):
            failures.append("non-monotonic or oversized uptime gap")
    else:
        epoch_delta = 0.0
        uptime_delta = 0.0
        gaps = []

    report = {
        "schema": "samurai-wifi-heartbeat-check-v1",
        "passed": not failures,
        "log": str(args.log),
        "log_sha256": sha256(args.log),
        "samples": len(rows),
        "exit_code": exit_code,
        "first_epoch": rows[0][0] if rows else None,
        "last_epoch": rows[-1][0] if rows else None,
        "first_uptime": rows[0][1] if rows else None,
        "last_uptime": rows[-1][1] if rows else None,
        "epoch_seconds": epoch_delta,
        "uptime_seconds": uptime_delta,
        "max_sample_gap_seconds": max(gaps) if gaps else None,
        "scope": "SSH process remained alive; link counters and boot identity are recorded separately.",
        "failures": failures,
    }
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
