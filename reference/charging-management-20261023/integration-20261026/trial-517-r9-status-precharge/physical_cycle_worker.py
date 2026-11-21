#!/usr/bin/python3
"""Observe one same-boot physical USB detach/reconnect cycle."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path


CLIENT = Path("/sys/bus/i2c/devices/0-005c")
PSY = Path("/sys/class/power_supply")
PROTECTION = Path("/devices/platform/samurai-gauge-protection/protection_state")
BOOT_ID = Path("/proc/sys/kernel/random/boot_id")
TAINT = Path("/proc/sys/kernel/tainted")
MANIFEST = Path("/usr/share/samurai-charging/manifest.json")
CRITICAL = (
    "WARNING:",
    "Oops:",
    "Kernel panic - not syncing",
    "refcount_t: underflow",
)


def _text(path: Path, default: str = "") -> str:
    try:
        return path.read_text().strip()
    except OSError:
        return default


def _atomic_json(path: Path, value: object) -> None:
    raw = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    tmp = path.with_name(path.name + ".next")
    with tmp.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    tmp.replace(path)


def _telemetry() -> dict:
    text = (CLIENT / "telemetry").read_text()
    return {key: int(value) for key, value in (item.split("=") for item in text.split())}


def _psy(name: str) -> str:
    return _text(PSY / name)


def _battery_name() -> str:
    candidates = []
    if PSY.is_dir():
        candidates = [
            path.name
            for path in PSY.iterdir()
            if path.is_dir() and _text(path / "type") == "Battery"
        ]
    return candidates[0] if len(candidates) == 1 else ""


def _sample() -> dict:
    telemetry = _telemetry()
    battery_name = _battery_name()
    udc_root = Path("/sys/class/udc")
    udc = next(iter(udc_root.iterdir()), None) if udc_root.is_dir() else None
    return {
        "epoch": time.time(),
        "boottime": time.clock_gettime(time.CLOCK_BOOTTIME),
        "telemetry": telemetry,
        "source_online": _psy("samurai-usb-input/online"),
        "source_current_max": _psy("samurai-usb-input/current_max"),
        "source_input_current_limit": _psy("samurai-usb-input/input_current_limit"),
        "source_usb_type": _psy("samurai-usb-input/usb_type"),
        "mp_input_current_limit": _psy("mp2650-input/input_current_limit"),
        "mp_status": _psy("mp2650-input/status"),
        "battery_name": battery_name,
        "battery_status": _psy(f"{battery_name}/status") if battery_name else "",
        "mp_health": _psy("mp2650-input/health"),
        "protection_health": _psy("samurai-gauge-protection/health"),
        "udc_state": _text(udc / "state") if udc else "",
    }


def healthy(sample: dict) -> bool:
    telemetry = sample["telemetry"]
    full_hold = full_hold_telemetry(telemetry)
    active = telemetry.get("desired_enable") == 1 and telemetry.get("full_holding") == 0
    return bool(
        telemetry.get("valid") == 1
        and telemetry.get("online") == 1
        and telemetry.get("protection_ok") == 1
        and telemetry.get("shadow") == 0
        and 0 <= telemetry.get("age_ms", -1) <= 3000
        and not any(
            telemetry.get(key, -1)
            for key in (
                "error",
                "stop_error",
                "latched",
                "source_inhibit",
                "fault",
                "cycle_timeout",
                "thermal_inhibit",
                "gauge_charge_stop",
            )
        )
        and (active or full_hold)
        and sample["source_online"] == "1"
        and sample["source_input_current_limit"] == "500000"
        and sample["mp_input_current_limit"] == "500000"
        and (
            (
                full_hold
                and sample["battery_name"]
                and sample["mp_status"] in ("Full", "Not charging")
                and sample["battery_status"] == "Full"
            )
            or (
                active
                and sample["battery_name"]
                and sample["mp_status"] in ("Charging", "Not charging")
                and sample["battery_status"] in ("Charging", "Not charging")
                and (
                    sample["mp_status"] == "Charging"
                    or sample["battery_status"] == "Charging"
                )
            )
        )
        and sample["mp_health"] == "Good"
        and sample["protection_health"] == "Good"
        and sample["udc_state"] == "configured"
    )


def full_hold_telemetry(telemetry: dict) -> bool:
    return bool(
        telemetry.get("desired_enable") == 0
        and telemetry.get("logical_full") == 1
        and telemetry.get("full_holding") == 1
        and telemetry.get("hold_requested") == 1
        and telemetry.get("full_cause") in (1, 2, 3)
    )


def detached(sample: dict) -> bool:
    telemetry = sample["telemetry"]
    return bool(
        telemetry.get("valid") == 1
        and telemetry.get("online") == 0
        and telemetry.get("desired_enable") == 0
        and telemetry.get("protection_ok") == 1
        and not any(
            telemetry.get(key, -1)
            for key in (
                "error",
                "stop_error",
                "latched",
                "source_inhibit",
                "fault",
            )
        )
        and sample["source_online"] == "0"
        and sample["protection_health"] == "Good"
    )


def safety_clean(sample: dict) -> bool:
    telemetry = sample["telemetry"]
    return bool(
        telemetry.get("protection_ok") == 1
        and not any(
            telemetry.get(key, -1)
            for key in ("error", "stop_error", "latched", "fault")
        )
        and sample["protection_health"] == "Good"
    )


def _span(rows: list[dict]) -> float:
    return rows[-1]["boottime"] - rows[0]["boottime"] if len(rows) >= 2 else 0.0


def classify_cycle(
    samples: list[dict],
    *,
    same_boot: bool,
    manifest_unchanged: bool,
    taint_before: int,
    taint_after: int,
    critical_delta: list[str],
) -> dict:
    detached_rows = [row for row in samples if detached(row)]
    if detached_rows:
        first_detach = samples.index(detached_rows[0])
        baseline = samples[max(0, first_detach - 3) : first_detach]
        detach_end = first_detach
        while detach_end < len(samples) and detached(samples[detach_end]):
            detach_end += 1
        detach_segment = samples[first_detach:detach_end]
        after = samples[detach_end:]
    else:
        first_detach = len(samples)
        baseline = samples[-3:]
        detach_segment = []
        after = []
    detached_span = _span(detach_segment)
    recovered_span = _span(after)
    before_session = baseline[-1]["telemetry"].get("session_seconds") if baseline else None
    after_session = after[-1]["telemetry"].get("session_seconds") if after else None
    after_full_hold = bool(after and full_hold_telemetry(after[-1]["telemetry"]))
    new_session = bool(
        before_session is not None
        and after_session is not None
        and after_session < before_session
    )
    checks = {
        "same_boot": same_boot,
        "manifest_unchanged": manifest_unchanged,
        "taint_unchanged": taint_before == taint_after,
        "no_new_critical_log": not critical_delta,
        "no_safety_fault_during_cycle": all(
            safety_clean(row) for row in samples[max(0, first_detach - 3) :]
        ),
        "healthy_baseline": len(baseline) == 3 and all(healthy(row) for row in baseline),
        "physical_detach_confirmed": (
            len(detach_segment) >= 3 and detached_span >= 2.0
        ),
        "automatic_recovery": (
            len(after) >= 15
            and recovered_span >= 14.0
            and all(healthy(row) for row in after)
        ),
        "fresh_session_or_full_hold": new_session or after_full_hold,
        "recovered_sdp_500ma": bool(
            after
            and after[-1]["source_online"] == "1"
            and after[-1]["source_input_current_limit"] == "500000"
            and after[-1]["mp_input_current_limit"] == "500000"
        ),
        "recovered_protection": bool(
            after
            and after[-1]["protection_health"] == "Good"
            and after[-1]["telemetry"].get("protection_ok") == 1
            and after[-1]["telemetry"].get("fault") == 0
        ),
    }
    return {
        "schema": 1,
        "accepted": all(checks.values()),
        "checks": checks,
        "samples": len(samples),
        "baseline_samples": len(baseline),
        "detached_samples": len(detach_segment),
        "detached_span_seconds": round(detached_span, 3),
        "recovered_samples": len(after),
        "recovered_span_seconds": round(recovered_span, 3),
        "session_before": before_session,
        "session_after": after_session,
        "new_session": new_session,
        "after_full_hold": after_full_hold,
        "same_boot": same_boot,
        "manifest_unchanged": manifest_unchanged,
        "taint_before": taint_before,
        "taint_after": taint_after,
        "no_safety_fault_during_cycle": checks["no_safety_fault_during_cycle"],
        "critical_log_delta": critical_delta,
        "physical_usb_cycle_proven": all(checks.values()),
    }


def _critical_delta(before: bytes, after: bytes) -> list[str]:
    if not after.startswith(before):
        return ["dmesg buffer did not preserve a comparable prefix"]
    tail = after[len(before) :].decode(errors="replace")
    return [value for value in CRITICAL if value in tail]


def _prepare_root(root: Path) -> None:
    if root.exists():
        if not root.is_dir() or any(root.iterdir()):
            raise RuntimeError("evidence root must be absent or empty")
    else:
        root.mkdir(parents=True, exist_ok=False, mode=0o700)


def run(root: Path, timeout: int) -> int:
    os.umask(0o077)
    try:
        _prepare_root(root)
        if os.geteuid() != 0:
            raise RuntimeError("root is required")
        initial_boot = _text(BOOT_ID)
        initial_manifest = hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
        initial_taint = int(_text(TAINT))
        initial_dmesg = subprocess.check_output(["dmesg"])
        samples = []
        baseline = 0
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            sample = _sample()
            samples.append(sample)
            baseline = baseline + 1 if healthy(sample) else 0
            if baseline >= 3:
                break
            time.sleep(1)
        if baseline < 3:
            raise RuntimeError("healthy three-sample baseline was not reached")
        _atomic_json(
            root / "ready.json",
            {
                "boot_id": initial_boot,
                "manifest_sha256": initial_manifest,
                "monotonic": time.monotonic(),
            },
        )
        go_deadline = time.monotonic() + 120
        while not (root / "go.json").exists():
            if time.monotonic() >= go_deadline:
                raise RuntimeError("go.json was not created within 120 seconds")
            time.sleep(0.2)
        go = json.loads((root / "go.json").read_text())
        if go.get("boot_id") != initial_boot:
            raise RuntimeError("go.json belongs to another boot")

        seen_detach = False
        detached_rows = []
        stable = 0
        end = time.monotonic() + timeout
        with (root / "samples.jsonl").open("x") as log:
            for row in samples:
                log.write(json.dumps(row, sort_keys=True) + "\n")
            log.flush()
            os.fsync(log.fileno())
            while time.monotonic() < end:
                sample = _sample()
                samples.append(sample)
                log.write(json.dumps(sample, sort_keys=True) + "\n")
                log.flush()
                os.fsync(log.fileno())
                if detached(sample):
                    seen_detach = True
                    detached_rows.append(sample)
                    stable = 0
                elif seen_detach:
                    if healthy(sample):
                        stable += 1
                        if stable >= 15:
                            break
                    else:
                        stable = 0
                if (root / "cancel").exists():
                    break
                time.sleep(1)

        final_dmesg = subprocess.check_output(["dmesg"])
        result = classify_cycle(
            samples,
            same_boot=_text(BOOT_ID) == initial_boot,
            manifest_unchanged=(
                hashlib.sha256(MANIFEST.read_bytes()).hexdigest() == initial_manifest
            ),
            taint_before=initial_taint,
            taint_after=int(_text(TAINT)),
            critical_delta=_critical_delta(initial_dmesg, final_dmesg),
        )
        _atomic_json(root / "result.json", result)
        _atomic_json(
            root / "terminal.json",
            {"terminal": True, "accepted": result["accepted"]},
        )
        return 0 if result["accepted"] else 1
    except BaseException as error:
        try:
            root.mkdir(parents=True, exist_ok=True, mode=0o700)
        except OSError:
            pass
        _atomic_json(
            root / "failure.json",
            {"terminal": True, "error": f"{type(error).__name__}: {error}"},
        )
        _atomic_json(root / "terminal.json", {"terminal": True, "accepted": False})
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=240)
    args = parser.parse_args()
    return run(args.root, args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())
