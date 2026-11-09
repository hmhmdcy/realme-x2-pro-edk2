#!/usr/bin/env python3
"""Probe the mainline Bluetooth PAN/HID host-module path on the handset.

Without --load this is read-only. With --load it uses the standard modprobe
interface, then verifies the BNEP socket family and the UHID/UINPUT character
devices. It does not pair, connect, bridge a PAN, or claim external HID input.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import time


RELEASE = "7.3.1-rmx1931-samurai-v731"
MODULES = {
    "bnep": "kernel/net/bluetooth/bnep/bnep.ko",
    "uhid": "kernel/drivers/hid/uhid.ko",
    "uinput": "kernel/drivers/input/misc/uinput.ko",
}
BTPROTO_BNEP = 4


def read(path: str) -> str | None:
    try:
        return Path(path).read_text(encoding="utf-8").strip()
    except OSError:
        return None


def command(*argv: str) -> dict:
    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return {
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"error": repr(error)}


def module_record(name: str) -> dict:
    path = Path("/usr/lib/modules") / os.uname().release / MODULES[name]
    record = {
        "name": name,
        "path": str(path),
        "file_present": path.is_file(),
        "loaded": Path(f"/sys/module/{name}").is_dir(),
    }
    if path.is_file():
        record["vermagic"] = command(
            "modinfo", "-F", "vermagic", str(path)
        ).get("stdout")
        record["intree"] = command(
            "modinfo", "-F", "intree", str(path)
        ).get("stdout")
        record["depends"] = command(
            "modinfo", "-F", "depends", str(path)
        ).get("stdout")
    return record


def bluez_view() -> dict:
    try:
        import dbus
    except ImportError:
        return {
            "available": False,
            "reason": "python3-dbus unavailable",
        }
    try:
        bus = dbus.SystemBus()
        manager = dbus.Interface(
            bus.get_object("org.bluez", "/"),
            "org.freedesktop.DBus.ObjectManager",
        )
        objects = manager.GetManagedObjects()
        adapters = []
        for path, interfaces in objects.items():
            adapter = interfaces.get("org.bluez.Adapter1")
            if adapter is None:
                continue
            adapters.append({
                "path": str(path),
                "address": str(adapter.get("Address", "")),
                "powered": bool(adapter.get("Powered", False)),
                "discovering": bool(adapter.get("Discovering", False)),
                "uuids": [
                    str(uuid) for uuid in adapter.get("UUIDs", [])
                ],
            })
        return {
            "available": True,
            "adapters": adapters,
            "connected_devices": sum(
                bool(
                    interfaces.get("org.bluez.Device1", {}).get(
                        "Connected", False
                    )
                )
                for interfaces in objects.values()
            ),
        }
    except Exception as error:
        return {"available": False, "reason": repr(error)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--load", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    release = os.uname().release
    before = {name: module_record(name) for name in MODULES}
    depmod_result = None
    load_results = None
    if args.load:
        depmod_result = command("depmod", "-A")
        load_results = {
            name: command("modprobe", name)
            for name in MODULES
        }
        time.sleep(0.5)
    after = {name: module_record(name) for name in MODULES}

    bnep_socket = {"passed": False}
    try:
        probe = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_RAW, BTPROTO_BNEP)
        probe.close()
        bnep_socket = {
            "passed": True,
            "family": int(socket.AF_BLUETOOTH),
            "protocol": BTPROTO_BNEP,
        }
    except OSError as error:
        bnep_socket["error"] = repr(error)

    uhid_device = Path("/dev/uhid")
    uinput_device = Path("/dev/uinput")
    char_devices = {}
    for name, path in [("uhid", uhid_device), ("uinput", uinput_device)]:
        record = {"path": str(path), "present": path.is_char_device()}
        if record["present"]:
            try:
                descriptor = os.open(path, os.O_RDWR | os.O_CLOEXEC)
                os.close(descriptor)
                record["opened"] = True
            except OSError as error:
                record["opened"] = False
                record["error"] = repr(error)
        char_devices[name] = record

    loader = Path("/usr/lib/modules-load.d/bluez.conf")
    loader_modules = (
        [
            line.strip()
            for line in loader.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        if loader.is_file()
        else None
    )
    bluez = bluez_view()
    checks = {
        "release_matches": release == RELEASE,
        "modules_have_matching_vermagic": all(
            record.get("vermagic")
            == f"{RELEASE} SMP preempt mod_unload aarch64"
            for record in after.values()
            if record["file_present"]
        ),
        "modules_are_intree": all(
            record.get("intree") == "Y"
            for record in after.values()
            if record["file_present"]
        ),
        "modules_loaded": all(record["loaded"] for record in after.values()),
        "module_load_commands_succeeded": (
            load_results is None
            or all(result.get("returncode") == 0 for result in load_results.values())
        ),
        "uhid_char_device_opened": char_devices["uhid"].get("opened") is True,
        "uinput_char_device_opened": (
            char_devices["uinput"].get("opened") is True
        ),
        "bnep_socket_family_registered": bnep_socket["passed"],
        "official_bluez_loader_present": loader_modules is not None,
        "bluez_adapter_present": (
            bluez.get("available") is True
            and bool(bluez.get("adapters"))
        ),
    }
    result = {
        "schema": "samurai-bluetooth-host-probe-v1",
        "passed": all(checks.values()),
        "release": release,
        "load_requested": args.load,
        "depmod_result": depmod_result,
        "load_results": load_results,
        "modules_before": before,
        "modules_after": after,
        "loader_path": str(loader),
        "loader_modules": loader_modules,
        "char_devices": char_devices,
        "bnep_socket": bnep_socket,
        "bluez": bluez,
        "checks": checks,
        "scope": (
            "Kernel ABI, character-device and socket-family checks only. "
            "No pairing, PAN peer, HID peer, routing or external input is "
            "claimed."
        ),
    }
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
