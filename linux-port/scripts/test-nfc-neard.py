#!/usr/bin/env python3
"""Probe the RMX1931 NFC block through nfc0 and the upstream neard D-Bus API."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time


NFC_CLASS = Path("/sys/class/nfc")
NEARD_SERVICE = "org.neard"
NEARD_ROOT = "/org/neard"
NFC_OBJECT = "/org/neard/nfc0"


def run(argv: list[str], timeout: float = 8.0) -> dict:
    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "argv": argv,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except (OSError, subprocess.TimeoutExpired) as error:
        return {
            "argv": argv,
            "returncode": None,
            "stdout": "",
            "stderr": str(error),
        }


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""


def nfc_devices() -> list[str]:
    return sorted(path.name for path in NFC_CLASS.glob("nfc*"))


def process_names() -> set[str]:
    result = run(["ps", "-eo", "comm="], timeout=4)
    if result["returncode"] != 0:
        return set()
    return {line.strip() for line in result["stdout"].splitlines() if line.strip()}


def dbus_send(interface: str, method: str, *arguments: str) -> dict:
    return run([
        "dbus-send",
        "--system",
        "--print-reply",
        f"--dest={NEARD_SERVICE}",
        NFC_OBJECT,
        f"{interface}.{method}",
        *arguments,
    ])


def adapter_properties() -> dict:
    return dbus_send(
        "org.freedesktop.DBus.Properties",
        "GetAll",
        "string:org.neard.Adapter",
    )


def adapter_set_property(name: str, value: str) -> dict:
    return dbus_send(
        "org.freedesktop.DBus.Properties",
        "Set",
        "string:org.neard.Adapter",
        f"string:{name}",
        value,
    )


def adapter_call(method: str, *arguments: str) -> dict:
    return dbus_send("org.neard.Adapter", method, *arguments)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--watch-seconds", type=float, default=8.0)
    parser.add_argument("--expect-tag", action="store_true")
    parser.add_argument("--keep-powered", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error("run as root")
    if not 1 <= args.watch_seconds <= 60:
        parser.error("--watch-seconds must be 1..60")

    result = {
        "schema": "samurai-nfc-neard-probe-v1",
        "boot_id": read_text(Path("/proc/sys/kernel/random/boot_id")),
        "release": read_text(Path("/proc/sys/kernel/osrelease")),
        "nfc_devices": nfc_devices(),
        "neard_service": None,
        "adapter_properties": None,
        "tag_seen": False,
        "tag_monitor": "",
        "checks": [],
        "errors": [],
    }
    checks = result["checks"]

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    check(
        "nfc0_present",
        "nfc0" in result["nfc_devices"],
        ", ".join(result["nfc_devices"]) or "none",
    )
    check(
        "neard_service_file",
        Path("/etc/init.d/neard").is_file(),
        "/etc/init.d/neard",
    )
    processes = process_names()
    if "neard" not in processes:
        start = run(["rc-service", "neard", "start"], timeout=10)
        check(
            "neard_started",
            start["returncode"] == 0,
            (start["stdout"] + start["stderr"]).strip(),
        )
        time.sleep(1.0)
        processes = process_names()
    check(
        "neard_process",
        "neard" in processes,
        "neard" if "neard" in processes else "not running",
    )

    service = run(["rc-service", "neard", "status"], timeout=5)
    result["neard_service"] = {
        "returncode": service["returncode"],
        "stdout": service["stdout"],
        "stderr": service["stderr"],
    }
    check(
        "neard_service_status",
        service["returncode"] == 0,
        (service["stdout"] + service["stderr"]).strip(),
    )

    properties = adapter_properties()
    result["adapter_properties"] = properties
    check(
        "neard_adapter_properties",
        properties["returncode"] == 0,
        (properties["stdout"] + properties["stderr"]).strip(),
    )

    monitor = None
    if properties["returncode"] == 0:
        monitor = subprocess.Popen(
            [
                "dbus-monitor",
                "--system",
                "type='signal',interface='org.neard.Adapter',member='TagFound'",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        time.sleep(0.5)
        powered = adapter_set_property("Powered", "variant:boolean:true")
        check(
            "adapter_powered",
            powered["returncode"] == 0,
            (powered["stdout"] + powered["stderr"]).strip(),
        )
        poll = adapter_call("StartPollLoop", "string:Initiator")
        check(
            "poll_loop_started",
            poll["returncode"] == 0,
            (poll["stdout"] + poll["stderr"]).strip(),
        )
        if poll["returncode"] == 0:
            time.sleep(args.watch_seconds)
        monitor.terminate()
        try:
            result["tag_monitor"] = monitor.communicate(timeout=3)[0]
        except subprocess.TimeoutExpired:
            monitor.kill()
            result["tag_monitor"] = monitor.communicate()[0]
        result["tag_seen"] = "member=TagFound" in result["tag_monitor"]
        stop = adapter_call("StopPollLoop")
        check(
            "poll_loop_stopped",
            stop["returncode"] == 0,
            (stop["stdout"] + stop["stderr"]).strip(),
        )
        if not args.keep_powered:
            off = adapter_set_property("Powered", "variant:boolean:false")
            check(
                "adapter_power_restored",
                off["returncode"] == 0,
                (off["stdout"] + off["stderr"]).strip(),
            )

    if args.expect_tag:
        check("tag_found", result["tag_seen"], "TagFound signal")
    result["taint"] = read_text(Path("/proc/sys/kernel/tainted"))
    result["dmesg_tail"] = run(["dmesg", "--color=never"], timeout=5)["stdout"].splitlines()[-60:]
    result["passed"] = all(item["passed"] for item in checks)
    result["scope"] = (
        "Checks the standard nfc0 device, the upstream neard service and "
        "D-Bus adapter polling. With --expect-tag it also requires a real "
        "TagFound signal; without a physical tag it makes no read/write claim."
    )
    if args.output:
        args.output.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
