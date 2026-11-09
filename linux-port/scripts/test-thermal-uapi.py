#!/usr/bin/env python3
"""Read-only probe of the standard Linux thermal class UAPI."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import tempfile


THERMAL_ROOT = Path("/sys/class/thermal")
REQUIRED_ZONES = {
    "camera-thermal",
    "cpu0-thermal",
    "gpu-top-thermal",
    "modem-thermal",
    "pm8150-thermal",
    "pm8150b-thermal",
    "pm8150l-thermal",
    "wlan-thermal",
}


def read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return None


def number(value: str | None) -> int | None:
    try:
        return int(value) if value is not None else None
    except ValueError:
        return None


def zone_record(path: Path) -> dict:
    record = {
        "path": str(path),
        "type": read(path / "type"),
        "temp_millidegree_c": number(read(path / "temp")),
        "mode": read(path / "mode"),
        "policy": read(path / "policy"),
        "trips": [],
    }
    indices = set()
    for item in path.glob("trip_point_*_temp"):
        match = re.fullmatch(r"trip_point_(\d+)_temp", item.name)
        if match:
            indices.add(int(match.group(1)))
    for index in sorted(indices):
        record["trips"].append({
            "index": index,
            "temp_millidegree_c": number(
                read(path / f"trip_point_{index}_temp")
            ),
            "hysteresis_millidegree_c": number(
                read(path / f"trip_point_{index}_hysteresis")
            ),
            "type": read(path / f"trip_point_{index}_type"),
        })
    return record


def cooling_record(path: Path) -> dict:
    return {
        "path": str(path),
        "type": read(path / "type"),
        "max_state": number(read(path / "max_state")),
        "current_state": number(read(path / "cur_state")),
    }


def scan(root: Path, min_zones: int) -> dict:
    zone_paths = (
        sorted(root.glob("thermal_zone[0-9]*")) if root.is_dir() else []
    )
    cooling_paths = (
        sorted(root.glob("cooling_device[0-9]*"))
        if root.is_dir()
        else []
    )
    zones = [zone_record(path) for path in zone_paths]
    cooling = [cooling_record(path) for path in cooling_paths]
    zone_types = {
        record["type"] for record in zones if record["type"]
    }
    trip_types = {
        trip["type"]
        for record in zones
        for trip in record["trips"]
        if trip["type"]
    }
    readings = [
        record["temp_millidegree_c"]
        for record in zones
        if record["temp_millidegree_c"] is not None
    ]
    cooling_types = {
        record["type"] for record in cooling if record["type"]
    }
    checks = {
        "thermal_class_present": root.is_dir(),
        "zone_count": len(zones) >= min_zones,
        "required_zone_types_present": REQUIRED_ZONES <= zone_types,
        "all_zones_have_type": all(
            record["type"] for record in zones
        ),
        "all_zone_temperatures_readable": (
            len(readings) == len(zones) and bool(zones)
        ),
        "zone_temperatures_plausible": all(
            -40000 <= value <= 150000 for value in readings
        ),
        "critical_trip_present": "critical" in trip_types,
        "passive_trip_present": "passive" in trip_types,
        "cooling_device_present": bool(cooling),
        "cpu_cooling_device_present": any(
            "cpu" in value.lower() or "cpufreq" in value.lower()
            for value in cooling_types
        ),
    }
    report = {
        "schema": "samurai-thermal-uapi-v1",
        "root": str(root),
        "passed": all(checks.values()),
        "mode": "read-only",
        "checks": checks,
        "zone_count": len(zones),
        "zone_types": sorted(zone_types),
        "missing_required_zone_types": sorted(REQUIRED_ZONES - zone_types),
        "trip_types": sorted(trip_types),
        "cooling_device_count": len(cooling),
        "cooling_types": sorted(cooling_types),
        "zones": zones,
        "cooling_devices": cooling,
        "scope": (
            "Standard thermal class discovery and read-only trip inspection. "
            "No trip, mode, policy or cooling state is written."
        ),
    }
    return report


def write_fixture(
    root: Path,
    include_passive: bool = True,
    include_cooling: bool = True,
) -> None:
    types = sorted(REQUIRED_ZONES)
    types.extend(f"aux{index}-thermal" for index in range(12))
    for index, zone_type in enumerate(types):
        zone = root / f"thermal_zone{index}"
        zone.mkdir(parents=True)
        (zone / "type").write_text(zone_type + "\n", encoding="utf-8")
        (zone / "temp").write_text("35000\n", encoding="utf-8")
        (zone / "mode").write_text("enabled\n", encoding="utf-8")
        (zone / "policy").write_text("step_wise\n", encoding="utf-8")
        if index < 2:
            trip_type = "critical" if index == 0 else "passive"
            (zone / "trip_point_0_temp").write_text(
                "110000\n" if index == 0 else "90000\n",
                encoding="utf-8",
            )
            (zone / "trip_point_0_hysteresis").write_text(
                "0\n" if index == 0 else "2000\n",
                encoding="utf-8",
            )
            (zone / "trip_point_0_type").write_text(
                trip_type + "\n", encoding="utf-8"
            )
    if not include_passive:
        (root / "thermal_zone1/trip_point_0_type").write_text(
            "hot\n", encoding="utf-8"
        )
    if include_cooling:
        cooling = root / "cooling_device0"
        cooling.mkdir()
        (cooling / "type").write_text("cpufreq-cpu0\n", encoding="utf-8")
        (cooling / "max_state").write_text("10\n", encoding="utf-8")
        (cooling / "cur_state").write_text("0\n", encoding="utf-8")


def self_test() -> dict:
    with tempfile.TemporaryDirectory(prefix="samurai-thermal-uapi-") as tmp:
        root = Path(tmp)
        write_fixture(root)
        valid = scan(root, 20)
        write_fixture(root / "invalid", include_passive=False,
                      include_cooling=False)
        invalid = scan(root / "invalid", 20)
    result = {
        "schema": "samurai-thermal-uapi-self-test-v1",
        "passed": valid["passed"] and not invalid["passed"],
        "valid_fixture": valid,
        "invalid_fixture": invalid,
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--root", type=Path, default=THERMAL_ROOT)
    parser.add_argument("--min-zones", type=int, default=20)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        report = self_test()
    else:
        report = scan(args.root, args.min_zones)
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
