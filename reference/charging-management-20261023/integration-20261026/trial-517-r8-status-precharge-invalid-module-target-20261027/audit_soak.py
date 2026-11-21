#!/usr/bin/env python3
"""Strictly audit charging-soak JSONL without touching the phone."""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import sys
from pathlib import Path


EXPECTED_BOOT = "97612ad1-d3ac-4721-b2b0-6d2456300559"
EXPECTED_MANIFEST = "e2ebdf7b7c94e7db8926d2cce70ff6a9bd059ea83492478710dcd45a7f7a93e8"
EXPECTED_VERSION = "#518 SMP PREEMPT Tue Oct 27 04:21:36 CST 2026"
EXPECTED_TAINT = 4096
ZERO_TELEMETRY_FIELDS = (
    "cycle_timeout",
    "error",
    "fault",
    "gauge_charge_stop",
    "latched",
    "source_inhibit",
    "stop_error",
    "thermal_inhibit",
)


def _timestamp(value: object) -> dt.datetime:
    if not isinstance(value, str):
        raise ValueError("missing timestamp")
    parsed = dt.datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("timestamp has no timezone")
    return parsed


def _sample_errors(row: dict, expected_boot: str, expected_manifest: str, expected_version: str) -> list[str]:
    errors = []
    if row.get("schema") != 1:
        errors.append("sample schema is not 1")
    if row.get("reachable") is not True:
        errors.append("sample is unreachable")
    if not isinstance(row.get("ssh_ip"), str) or not row["ssh_ip"]:
        errors.append("sample has no transport address")
    if not isinstance(row.get("sample_seconds"), (int, float)) or row["sample_seconds"] > 30:
        errors.append("sample took longer than 30 seconds")

    device = row.get("device")
    if not isinstance(device, dict):
        errors.append("device snapshot is missing")
        return errors
    if device.get("boot_id") != expected_boot:
        errors.append("unexpected boot id")
    if device.get("audit_boot") != expected_boot or device.get("accepted_boot") != expected_boot:
        errors.append("audit or acceptance evidence belongs to another boot")
    if device.get("audit_passed") is not True:
        errors.append("automatic audit did not pass")
    if device.get("audit_manifest_sha256") != expected_manifest:
        errors.append("manifest hash mismatch")
    if device.get("state_event") != "accepted":
        errors.append("guard state is not accepted")
    if expected_version not in str(device.get("version")):
        errors.append("kernel version mismatch")
    if device.get("protection_health") != "Good":
        errors.append("protection health is not Good")
    if device.get("battery_health") != "Good" or device.get("mp_health") != "Good":
        errors.append("battery or charger health is not Good")
    if device.get("mp_online") != 1:
        errors.append("charger input is offline")
    if not 4_400_000 <= int(device.get("tcpm_voltage_uv") or 0) <= 5_500_000:
        errors.append("TCPM voltage is outside the fixed 5 V window")
    if int(device.get("tcpm_current_ua") or 0) <= 0:
        errors.append("TCPM current is not positive")
    if not 6_000_000 <= int(device.get("battery_voltage_uv") or 0) <= 9_000_000:
        errors.append("battery pack voltage is outside the expected 2S range")
    if not -100 <= int(device.get("battery_temp_decic") or 10_000) <= 450:
        errors.append("battery temperature is outside -10..45 C")
    if device.get("tainted") != str(EXPECTED_TAINT):
        errors.append("unexpected kernel taint mask")

    telemetry = device.get("telemetry")
    if not isinstance(telemetry, dict):
        errors.append("managed telemetry is missing")
        return errors
    if telemetry.get("valid") != 1 or telemetry.get("online") != 1:
        errors.append("managed telemetry is not valid and online")
    if telemetry.get("protection_ok") != 1 or telemetry.get("shadow") != 0:
        errors.append("protection is not healthy or telemetry is in shadow mode")
    if not 0 <= int(telemetry.get("age_ms", -1)) <= 3000:
        errors.append("managed telemetry is stale")
    for field in ZERO_TELEMETRY_FIELDS:
        if telemetry.get(field) != 0:
            errors.append(f"telemetry {field} is nonzero")

    full_hold = (
        telemetry.get("desired_enable") == 0
        and telemetry.get("logical_full") == 1
        and telemetry.get("full_holding") == 1
        and telemetry.get("hold_requested") == 1
        and telemetry.get("full_cause") in (1, 2, 3)
    )
    active = telemetry.get("desired_enable") == 1 and telemetry.get("full_holding") == 0
    if not active and not full_hold:
        errors.append("charging state is neither active nor an explicit Full hold")

    zones = device.get("thermal_zones")
    if not isinstance(zones, dict) or not zones:
        errors.append("thermal zones are missing")
    else:
        for name, zone in zones.items():
            value = zone.get("temp_millideg") if isinstance(zone, dict) else None
            if not isinstance(value, int) or not -20_000 <= value <= 80_000:
                errors.append(f"thermal zone {name} is outside -20..80 C")
    return errors


def audit(
    rows: list[dict],
    *,
    expected_boot: str = EXPECTED_BOOT,
    expected_manifest: str = EXPECTED_MANIFEST,
    expected_version: str = EXPECTED_VERSION,
    minimum_samples: int = 1,
    minimum_span_seconds: float = 0,
    maximum_gap_seconds: float = 120,
) -> dict:
    errors = []
    timestamps = []
    transports = collections.Counter()
    boot_ids = set()
    max_gap = 0.0
    for index, row in enumerate(rows, 1):
        try:
            timestamps.append(_timestamp(row.get("timestamp")))
        except (TypeError, ValueError) as error:
            errors.append(f"sample {index}: {error}")
        if isinstance(row.get("ssh_ip"), str):
            transports[row["ssh_ip"]] += 1
        device = row.get("device")
        if isinstance(device, dict) and isinstance(device.get("boot_id"), str):
            boot_ids.add(device["boot_id"])
        for error in _sample_errors(row, expected_boot, expected_manifest, expected_version):
            errors.append(f"sample {index}: {error}")
    for previous, current in zip(timestamps, timestamps[1:]):
        gap = (current - previous).total_seconds()
        if gap < 0:
            errors.append("sample timestamps are not monotonic")
        max_gap = max(max_gap, gap)
    span = (timestamps[-1] - timestamps[0]).total_seconds() if len(timestamps) >= 2 else 0.0
    if len(rows) < minimum_samples:
        errors.append(f"only {len(rows)} samples, need at least {minimum_samples}")
    if span < minimum_span_seconds:
        errors.append(f"sample span is {span:.1f}s, need at least {minimum_span_seconds:.1f}s")
    if max_gap > maximum_gap_seconds:
        errors.append(f"maximum sample gap is {max_gap:.1f}s")
    if boot_ids != {expected_boot}:
        errors.append(f"unexpected boot set: {sorted(boot_ids)}")
    usb_rows = transports.get("169.254.42.1", 0)
    return {
        "schema": 1,
        "passed": not errors,
        "scope": "charging stability only; transport channel does not prove a physical USB cycle",
        "samples": len(rows),
        "sample_span_seconds": round(span, 3),
        "maximum_gap_seconds": round(max_gap, 3),
        "boot_ids": sorted(boot_ids),
        "transport_counts": dict(transports),
        "usb_transport_samples": usb_rows,
        "physical_usb_cycle_proven": False,
        "errors": errors,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("jsonl", type=Path)
    parser.add_argument("--minimum-samples", type=int, default=570)
    parser.add_argument("--minimum-span-seconds", type=float, default=34_200)
    parser.add_argument("--maximum-gap-seconds", type=float, default=120)
    parser.add_argument("--allow-partial", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    rows = [json.loads(line) for line in args.jsonl.read_text().splitlines() if line.strip()]
    minimum_samples = min(args.minimum_samples, len(rows)) if args.allow_partial else args.minimum_samples
    minimum_span = 0 if args.allow_partial else args.minimum_span_seconds
    report = audit(
        rows,
        minimum_samples=minimum_samples,
        minimum_span_seconds=minimum_span,
        maximum_gap_seconds=args.maximum_gap_seconds,
    )
    raw = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(raw)
    print(raw, end="")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
