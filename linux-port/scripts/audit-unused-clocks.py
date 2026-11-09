#!/usr/bin/env python3
"""Inventory hardware-enabled clocks that have no logical consumer."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def parse_summary(path: Path) -> list[dict[str, object]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if (
            len(fields) < 10
            or not all(field.isdigit() for field in fields[1:8])
            or fields[8] not in {"Y", "N"}
        ):
            continue
        rows.append(
            {
                "clock": fields[0],
                "enable_count": int(fields[1]),
                "prepare_count": int(fields[2]),
                "protect_count": int(fields[3]),
                "rate": int(fields[4]),
                "hardware_enable": fields[8],
                "consumer": fields[9],
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("clk_summary", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    rows = parse_summary(args.clk_summary)
    candidates = [
        row
        for row in rows
        if row["hardware_enable"] == "Y"
        and row["enable_count"] == 0
        and row["prepare_count"] == 0
        and row["protect_count"] == 0
    ]
    report = {
        "schema": "samurai-clk-unused-audit-v1",
        "source": str(args.clk_summary),
        "source_sha256": hashlib.sha256(args.clk_summary.read_bytes()).hexdigest(),
        "clock_count": len(rows),
        "hardware_enabled_without_consumer_count": len(candidates),
        "hardware_enabled_without_consumer": candidates,
        "note": (
            "This is an inventory, not proof that each clock is critical. "
            "Parent clocks and PLLs can legitimately remain enabled while a "
            "child consumer is active."
        ),
    }
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
