#!/usr/bin/python3
"""One physical USB insertion/removal s2idle wake probe.

The worker changes no charger registers. It programs one RTC safety alarm,
writes System sleep state once, and classifies evidence after resume. RTC wake
is always invalid for acceptance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path


PSY = Path("/sys/class/power_supply/samurai-usb-input")
MEM_SLEEP = Path("/sys/power/mem_sleep")
SUSPEND_STATS = Path("/sys/power/suspend_stats")
WAKEUP_IRQ = Path("/sys/power/pm_wakeup_irq")
WAKEUP_SOURCES = Path("/sys/power/wakeup_sources")
RTC_WAKEALARM = Path("/sys/class/rtc/rtc0/wakealarm")
RTC_WAKEUP = Path("/sys/class/rtc/rtc0/device/power/wakeup")
BOOT_ID = Path("/proc/sys/kernel/random/boot_id")
VERSION = Path("/proc/version")
INTERRUPTS = Path("/proc/interrupts")

DEFAULT_ALARM_SECONDS = 180
PRE_SUSPEND_DELAY_SECONDS = 15


def _text(path: Path, default: str = "") -> str:
    try:
        return path.read_text().strip()
    except OSError:
        return default


def _integer(path: Path) -> int | None:
    value = _text(path)
    try:
        return int(value)
    except ValueError:
        return None


def _atomic_json(path: Path, value: object) -> None:
    raw = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    tmp = path.with_name(path.name + ".next")
    with tmp.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    tmp.replace(path)
    fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _interrupts() -> dict:
    text = INTERRUPTS.read_text()
    rows = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, tail = line.split(":", 1)
        if not key.strip().isdigit():
            continue
        counts = []
        for field in tail.split():
            if not field.isdigit():
                break
            counts.append(int(field))
        if counts:
            rows[int(key)] = {"count": sum(counts), "line": line}
    return {
        "sha256": hashlib.sha256(text.encode()).hexdigest(),
        "rows": rows,
    }


def _scan_wakeup_sources() -> dict:
    result = {}
    for line in _text(WAKEUP_SOURCES).splitlines():
        fields = line.split()
        if not fields:
            continue
        name = fields[0]
        row = {"line": line}
        for index, field in enumerate(fields[1:], 1):
            if ":" not in field:
                continue
            key, value = field.split(":", 1)
            row[key] = int(value) if value.isdigit() else value
        result[name] = row
    return result


def _stats() -> dict:
    result = {}
    for path in SUSPEND_STATS.iterdir():
        if path.is_file() and path.read_text().strip().isdigit():
            result[path.name] = int(path.read_text())
    return result


def _dmesg() -> dict:
    raw = subprocess.check_output(["dmesg"])
    return {
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "tail": raw[-20000:].decode(errors="replace"),
    }


def _psy() -> dict:
    values = {}
    for name in (
        "online",
        "current_max",
        "input_current_limit",
        "status",
        "usb_type",
        "power/wakeup",
    ):
        values[name] = _text(PSY / name)
    return values


def _snapshot() -> dict:
    return {
        "boot_id": _text(BOOT_ID),
        "version": _text(VERSION),
        "boottime_ns": time.clock_gettime_ns(time.CLOCK_BOOTTIME),
        "epoch": time.time(),
        "mem_sleep": _text(MEM_SLEEP),
        "rtc_alarm": _text(RTC_WAKEALARM),
        "rtc_wakeup": _text(RTC_WAKEUP),
        "pm_wakeup_irq": _text(WAKEUP_IRQ),
        "psy": _psy(),
        "stats": _stats(),
        "interrupts": _interrupts(),
        "wakeup_sources": _scan_wakeup_sources(),
        "dmesg": _dmesg(),
    }


def _find_event_irqs(interrupts: dict, names: list[str]) -> dict[str, int]:
    result = {}
    for name in names:
        matches = [
            irq
            for irq, row in interrupts["rows"].items()
            if row["line"].split()[-1] == name
        ]
        if len(matches) != 1:
            raise RuntimeError(f"expected exactly one IRQ named {name}: {matches}")
        result[name] = matches[0]
    return result


def _event_state(mode: str, snapshot: dict) -> bool:
    online = snapshot["psy"].get("online")
    if mode == "insert":
        return online == "1"
    if mode == "remove":
        return online == "0"
    raise ValueError(mode)


def _row_count(rows: dict, irq: int | None) -> int:
    if irq is None:
        return 0
    row = rows.get(irq)
    if row is None:
        row = rows.get(str(irq), {})
    return int(row.get("count", 0))


def classify(
    mode: str,
    before: dict,
    after: dict,
    *,
    event_irqs: dict[str, int],
    rtc_irq: int | None,
    request_epoch: float,
    alarm_seconds: int,
) -> dict:
    errors = []
    stats_before = before["stats"]
    stats_after = after["stats"]
    success_delta = stats_after.get("success", 0) - stats_before.get("success", 0)
    fail_delta = stats_after.get("fail", 0) - stats_before.get("fail", 0)
    if success_delta != 1 or fail_delta != 0:
        errors.append(f"suspend_stats delta success={success_delta} fail={fail_delta}")
    if before["boot_id"] != after["boot_id"]:
        errors.append("boot id changed")
    if before["version"] != after["version"] or "#517 " not in after["version"]:
        errors.append("kernel version changed or is not #517")
    if before["mem_sleep"] != "[s2idle]" or after["mem_sleep"] != "[s2idle]":
        errors.append("s2idle is not the active sleep state")

    before_online = before["psy"].get("online")
    after_online = after["psy"].get("online")
    expected_before = "0" if mode == "insert" else "1"
    if before_online != expected_before:
        errors.append(f"unexpected pre-test USB online state: {before_online}")
    if not _event_state(mode, after):
        errors.append(f"post-test USB state does not prove {mode}")
    if mode == "insert" and after["psy"].get("input_current_limit") != "500000":
        errors.append("inserted source did not recover the 500mA SDP allowance")

    target_deltas = {}
    for name, irq in event_irqs.items():
        previous = _row_count(before["interrupts"]["rows"], irq)
        current = _row_count(after["interrupts"]["rows"], irq)
        target_deltas[name] = current - previous
    if not any(delta > 0 for delta in target_deltas.values()):
        errors.append("neither owned USB event IRQ advanced")

    rtc_before = _row_count(before["interrupts"]["rows"], rtc_irq) if rtc_irq is not None else None
    rtc_after = _row_count(after["interrupts"]["rows"], rtc_irq) if rtc_irq is not None else None
    rtc_delta = (
        None
        if rtc_before is None or rtc_after is None
        else rtc_after - rtc_before
    )
    if rtc_delta == 0:
        pass
    elif rtc_delta is None:
        errors.append("RTC IRQ could not be identified")
    else:
        errors.append(f"RTC IRQ advanced by {rtc_delta}")

    residency = after["epoch"] - request_epoch
    if residency >= alarm_seconds - 10:
        errors.append(f"resume time is consistent with RTC fallback: {residency:.3f}s")

    pm_wakeup_irq = after.get("pm_wakeup_irq")
    wake_irq_match = pm_wakeup_irq in {str(irq) for irq in event_irqs.values()}

    before_log = before["dmesg"]
    after_log = after["dmesg"]
    log_delta = ""
    if after_log["bytes"] >= before_log["bytes"]:
        after_tail = after_log.get("tail", "")
        before_tail = before_log.get("tail", "")
        if after_tail.startswith(before_tail):
            log_delta = after_tail[len(before_tail) :]
    if not log_delta:
        errors.append("dmesg delta is unavailable")
    critical = [
        value
        for value in (
            "WARNING:",
            "Oops:",
            "Kernel panic - not syncing",
            "refcount_t: underflow",
        )
        if value in log_delta
    ]
    if critical:
        errors.append(f"critical kernel log delta: {critical}")
    if "PM: suspend entry (s2idle)" not in log_delta:
        errors.append("missing s2idle entry in dmesg delta")
    if "PM: suspend exit" not in log_delta:
        errors.append("missing s2idle exit in dmesg delta")

    return {
        "schema": 1,
        "mode": mode,
        "accepted": not errors,
        "errors": errors,
        "same_boot": before["boot_id"] == after["boot_id"],
        "boot_id": after["boot_id"],
        "suspend_stats_delta": {"success": success_delta, "fail": fail_delta},
        "estimated_residency_seconds": round(residency, 3),
        "event_irqs": event_irqs,
        "event_irq_deltas": target_deltas,
        "rtc_irq": rtc_irq,
        "rtc_irq_delta": rtc_delta,
        "pm_wakeup_irq": pm_wakeup_irq,
        "pm_wakeup_irq_is_owned_event": wake_irq_match,
        "usb_before_online": before_online,
        "usb_after_online": after_online,
        "usb_after_current_limit": after["psy"].get("input_current_limit"),
        "critical_log_delta": critical,
    }


def run(root: Path, mode: str, alarm_seconds: int) -> int:
    os.umask(0o077)
    root.mkdir(parents=True, exist_ok=False, mode=0o700)
    try:
        if os.geteuid() != 0:
            raise RuntimeError("root is required")
        if _text(MEM_SLEEP) != "[s2idle]":
            raise RuntimeError(f"s2idle is not selected: {_text(MEM_SLEEP)!r}")
        if _text(RTC_WAKEALARM):
            raise RuntimeError("rtc0 wakealarm is not clear")
        if _text(RTC_WAKEUP) != "enabled":
            raise RuntimeError("rtc0 wakeup is not enabled")
        if _text(PSY / "power/wakeup") != "enabled":
            raise RuntimeError("samurai-usb-input wakeup is not enabled")

        initial = _snapshot()
        event_irqs = _find_event_irqs(
            initial["interrupts"],
            ["usbin-plugin", "usbin-src-change"],
        )
        rtc_matches = [
            irq
            for irq, row in initial["interrupts"]["rows"].items()
            if row["line"].split()[-1] == "rtc0"
        ]
        rtc_irq = rtc_matches[0] if len(rtc_matches) == 1 else None
        _atomic_json(
            root / "ready.json",
            {
                "boot_id": initial["boot_id"],
                "mode": mode,
                "event_irqs": event_irqs,
                "rtc_irq": rtc_irq,
                "alarm_seconds": alarm_seconds,
                "pre_suspend_delay_seconds": PRE_SUSPEND_DELAY_SECONDS,
                "monotonic": time.monotonic(),
            },
        )
        deadline = time.monotonic() + 240
        while not (root / "go.json").exists():
            if time.monotonic() >= deadline:
                raise RuntimeError("go.json was not created within 240 seconds")
            time.sleep(0.2)
        go = json.loads((root / "go.json").read_text())
        if go.get("boot_id") != initial["boot_id"]:
            raise RuntimeError("go.json belongs to another boot")

        time.sleep(PRE_SUSPEND_DELAY_SECONDS)
        if _text(BOOT_ID) != initial["boot_id"]:
            raise RuntimeError("boot changed before suspend")
        before = _snapshot()
        alarm_epoch = int(time.time()) + alarm_seconds
        RTC_WAKEALARM.write_text(str(alarm_epoch))
        request_epoch = time.time()
        _atomic_json(
            root / "before.json",
            {
                **before,
                "alarm_epoch": alarm_epoch,
                "request_epoch": request_epoch,
            },
        )
        (root / "mem-write-once.json").write_text(
            json.dumps({"boot_id": initial["boot_id"], "writes": 1}) + "\n"
        )
        Path("/sys/power/state").write_text("mem\n")
        after = _snapshot()
        try:
            RTC_WAKEALARM.write_text("0")
        except OSError:
            pass
        _atomic_json(root / "after.json", after)
        result = classify(
            mode,
            before,
            after,
            event_irqs=event_irqs,
            rtc_irq=rtc_irq,
            request_epoch=request_epoch,
            alarm_seconds=alarm_seconds,
        )
        _atomic_json(root / "result.json", result)
        _atomic_json(
            root / "terminal.json",
            {"terminal": True, "accepted": result["accepted"]},
        )
        return 0 if result["accepted"] else 1
    except BaseException as error:
        _atomic_json(
            root / "failure.json",
            {"terminal": True, "error": f"{type(error).__name__}: {error}"},
        )
        _atomic_json(root / "terminal.json", {"terminal": True, "accepted": False})
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--mode", choices=("insert", "remove"), required=True)
    parser.add_argument("--alarm-seconds", type=int, default=DEFAULT_ALARM_SECONDS)
    args = parser.parse_args()
    return run(args.root, args.mode, args.alarm_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
