#!/usr/bin/env python3
"""Validate a completed USB NCM stability result against the acceptance matrix."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


REQUIRED_SIZES = (65536, 262144, 1048576, 4194304)
REQUIRED_DIRECTIONS = ("upload", "download")
HEX = set("0123456789abcdef")


def load_result(path: Path) -> dict[str, Any]:
    if path.is_dir():
        path = path / "result.json"
    return json.loads(path.read_text(encoding="utf-8"))


def digest_ok(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in HEX for character in value.lower())
    )


def command_ok(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and value.get("returncode") == 0
        and value.get("timed_out") is False
    )


def add_failure(failures: list[str], condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


def validate(
    result: dict[str, Any],
    source: Path,
    min_iterations: int,
    heartbeat_seconds: int,
    expected_release: str,
) -> dict[str, Any]:
    failures: list[str] = []
    add_failure(failures, result.get("schema") == "samurai-usb-ncm-stability-v1",
                "schema mismatch")
    add_failure(failures, result.get("dry_run") is False, "result is a dry run")
    matrix = result.get("matrix", {})
    add_failure(failures, matrix.get("directions") == "both",
                "matrix is not bidirectional")
    sizes = matrix.get("sizes")
    add_failure(failures, isinstance(sizes, list) and
                tuple(sizes) == REQUIRED_SIZES,
                f"matrix sizes are not {REQUIRED_SIZES}")
    iterations = matrix.get("iterations")
    add_failure(failures, isinstance(iterations, int) and
                iterations >= min_iterations,
                f"matrix has fewer than {min_iterations} iterations")
    transfers = result.get("transfers")
    add_failure(failures, isinstance(transfers, list), "missing transfers")
    transfers = transfers if isinstance(transfers, list) else []

    expected_keys = {
        (direction, size, iteration)
        for direction in REQUIRED_DIRECTIONS
        for size in REQUIRED_SIZES
        for iteration in range(1, min_iterations + 1)
    }
    actual_keys = {
        (
            record.get("direction"),
            record.get("size"),
            record.get("iteration"),
        )
        for record in transfers
        if isinstance(record, dict)
    }
    add_failure(failures, expected_keys.issubset(actual_keys),
                "matrix is incomplete")
    for key in sorted(expected_keys - actual_keys):
        failures.append(f"missing transfer {key[0]} size={key[1]} iteration={key[2]}")

    for record in transfers:
        if not isinstance(record, dict):
            failures.append("non-object transfer entry")
            continue
        direction = record.get("direction")
        size = record.get("size")
        iteration = record.get("iteration")
        label = f"{direction}/size={size}/iteration={iteration}"
        add_failure(failures, record.get("passed") is True,
                    f"{label}: not passed")
        add_failure(failures, record.get("bytes") == size,
                    f"{label}: byte count mismatch")
        add_failure(failures, digest_ok(record.get("expected_sha256")),
                    f"{label}: invalid expected SHA-256")
        add_failure(failures, record.get("actual_sha256") ==
                    record.get("expected_sha256"),
                    f"{label}: SHA-256 mismatch")
        transfer = record.get("transfer", {})
        add_failure(failures, command_ok(transfer),
                    f"{label}: transfer command failed")
        if direction == "upload":
            add_failure(failures, command_ok(record.get("verification", {})),
                        f"{label}: remote verification failed")
            add_failure(failures, record.get("remote_bytes") == size,
                        f"{label}: remote byte count mismatch")
        elif direction == "download":
            add_failure(failures, command_ok(record.get("prepare", {})),
                        f"{label}: remote preparation failed")
            add_failure(failures, record.get("remote_bytes") == size,
                        f"{label}: prepared byte count mismatch")
        else:
            failures.append(f"{label}: unknown direction")

    for key in ("device_pre", "device_post"):
        snapshot = result.get(key, {})
        add_failure(failures, command_ok(snapshot),
                    f"{key}: SSH snapshot failed")
        parsed = snapshot.get("parsed", {}) if isinstance(snapshot, dict) else {}
        add_failure(failures, parsed.get("taint") == "0",
                    f"{key}: taint is not zero")
        add_failure(failures, parsed.get("release") == expected_release,
                    f"{key}: unexpected release")
        add_failure(failures, parsed.get("carrier") == "1",
                    f"{key}: NCM carrier is not 1")
        add_failure(failures, bool(parsed.get("bound")),
                    f"{key}: gadget is not bound")
        add_failure(failures, "configured" in parsed.values(),
                    f"{key}: UDC is not configured")
    pre = result.get("device_pre", {})
    post = result.get("device_post", {})
    pre = pre.get("parsed", {}) if isinstance(pre, dict) else {}
    post = post.get("parsed", {}) if isinstance(post, dict) else {}
    add_failure(failures, bool(pre.get("boot_id")) and
                pre.get("boot_id") == post.get("boot_id"),
                "boot ID changed during the matrix")

    heartbeat = result.get("heartbeat", {})
    if not isinstance(heartbeat, dict):
        heartbeat = {}
    requested = heartbeat.get("requested_seconds")
    add_failure(failures, isinstance(requested, int) and
                requested >= heartbeat_seconds,
                f"heartbeat shorter than {heartbeat_seconds}s")
    add_failure(failures, heartbeat.get("passed") is True,
                "heartbeat failed")
    add_failure(failures, heartbeat.get("first_failure") is None,
                "heartbeat recorded a failure")
    add_failure(failures, bool(heartbeat.get("samples")),
                "heartbeat has no samples")
    summary = result.get("summary", {})
    add_failure(failures, isinstance(summary, dict) and
                summary.get("passed") is True,
                "harness summary is not passed")

    return {
        "schema": "samurai-usb-ncm-result-check-v1",
        "result_path": str(source),
        "result_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "passed": not failures,
        "failures": failures,
        "expected": {
            "sizes": list(REQUIRED_SIZES),
            "direction": "both",
            "iterations": min_iterations,
            "heartbeat_seconds": heartbeat_seconds,
            "release": expected_release,
        },
        "observed": {
            "transfers": len(transfers),
            "boot_id": pre.get("boot_id"),
            "taint_pre": pre.get("taint"),
            "taint_post": post.get("taint"),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", type=Path)
    parser.add_argument("--min-iterations", type=int, default=3)
    parser.add_argument("--heartbeat-seconds", type=int, default=1800)
    parser.add_argument("--expected-release", default="7.3.1-rmx1931-samurai-v731")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.min_iterations <= 0:
        parser.error("--min-iterations must be positive")
    if args.heartbeat_seconds < 0:
        parser.error("--heartbeat-seconds cannot be negative")
    source = args.result
    if source.is_dir():
        source = source / "result.json"
    if not source.is_file():
        print(f"result file not found: {source}", file=sys.stderr)
        return 2
    result = load_result(source)
    report = validate(
        result,
        source,
        args.min_iterations,
        args.heartbeat_seconds,
        args.expected_release,
    )
    if args.output:
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
