#!/usr/bin/env python3
"""Exercise the RMX1931 rear flash through the standard Linux LED class."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time


LED_ROOT = Path("/sys/class/leds")
THERMAL_ROOT = Path("/sys/class/thermal")


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""


def write_text(path: Path, value: str) -> None:
    path.write_text(value + "\n", encoding="utf-8")


def command(argv: list[str], timeout: float = 8.0) -> dict:
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


def optional_text(path: Path) -> str:
    value = read_text(path)
    return value if value else "unknown"


def identify_led() -> Path:
    candidates = []
    for path in sorted(LED_ROOT.glob("*")):
        if not path.is_dir():
            continue
        identity = " ".join([
            path.name,
            read_text(path / "function"),
            read_text(path / "color"),
            read_text(path / "label"),
        ]).lower()
        if "flash" in identity or "torch" in identity:
            candidates.append(path)
    if not candidates:
        raise RuntimeError("no flash/torch LED class device found")
    white = [path for path in candidates if "white" in path.name.lower()]
    if len(white) == 1:
        return white[0]
    if len(candidates) == 1:
        return candidates[0]
    raise RuntimeError(
        "ambiguous flash LEDs: " + ", ".join(path.name for path in candidates)
    )


def thermal_snapshot() -> list[dict]:
    zones = []
    for path in sorted(THERMAL_ROOT.glob("thermal_zone*")):
        zone_type = read_text(path / "type")
        temperature = read_text(path / "temp")
        if not zone_type or not temperature:
            continue
        zones.append({
            "zone": path.name,
            "type": zone_type,
            "millidegree_c": int(temperature),
        })
    return zones


def dmesg_tail() -> list[str]:
    result = command(["dmesg", "--color=never"], timeout=5)
    if result["returncode"] != 0:
        return []
    return result["stdout"].splitlines()[-120:]


def flash_subdevices() -> list[dict]:
    devices = []
    for path in sorted(Path("/dev").glob("v4l-subdev*")):
        result = command(["v4l2-ctl", "-d", str(path), "--list-ctrls"])
        if result["returncode"] != 0:
            continue
        text = result["stdout"]
        if not re.search(r"(?im)^\s*Flash Controls\s*$", text):
            continue
        names = [
            match.group(1)
            for line in text.splitlines()
            if (match := re.match(r"(?i)^\s*([a-z][a-z0-9_]*)\b", line))
        ]
        controls = {}
        for name in ("strobe_status", "faults"):
            if name not in names:
                continue
            current = command([
                "v4l2-ctl",
                "-d",
                str(path),
                f"--get-ctrl={name}",
            ])
            value = None
            if ":" in current["stdout"]:
                value = current["stdout"].rsplit(":", 1)[1].strip()
            controls[name] = {
                "returncode": current["returncode"],
                "value": value,
                "stderr": current["stderr"],
            }
        devices.append({
            "device": str(path),
            "available_controls": names,
            "controls": controls,
        })
    return devices


def parse_control_integer(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value, 0)
    except ValueError:
        return None


def v4l2_control(device: str, name: str, value: str | None = None) -> dict:
    argv = ["v4l2-ctl", "-d", device]
    if value is None:
        argv.append(f"--get-ctrl={name}")
    else:
        argv.append(f"--set-ctrl={name}={value}")
    return command(argv)


def v4l2_control_value(result: dict) -> int | None:
    text = result.get("stdout", "")
    match = re.search(r":\s*(-?\d+)", text)
    if not match:
        return None
    return int(match.group(1))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fraction", type=float, default=0.10)
    parser.add_argument("--hold-ms", type=int, default=750)
    parser.add_argument("--torch-intensity-ua", type=int, default=200000)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error("run as root")
    if not 0 < args.fraction <= 1:
        parser.error("--fraction must be in (0, 1]")
    if not 100 <= args.hold_ms <= 5000:
        parser.error("--hold-ms must be 100..5000")
    if not 0 < args.torch_intensity_ua <= 1000000:
        parser.error("--torch-intensity-ua must be in 1..1000000")

    compatible = read_text(Path("/sys/firmware/devicetree/base/compatible"))
    compatible_values = [item for item in compatible.split("\0") if item]
    if "realme,samurai" not in compatible_values:
        raise RuntimeError("Samurai device required")

    led = identify_led()
    max_brightness = int(read_text(led / "max_brightness"))
    level = max(1, round(max_brightness * args.fraction))
    before_temperatures = thermal_snapshot()
    before_dmesg = dmesg_tail()
    before_taint = read_text(Path("/proc/sys/kernel/tainted"))

    result = {
        "schema": "samurai-flash-led-test-v1",
        "boot_id": read_text(Path("/proc/sys/kernel/random/boot_id")),
        "release": read_text(Path("/proc/sys/kernel/osrelease")),
        "compatible": compatible_values,
        "led": str(led),
        "led_name": led.name,
        "max_brightness": max_brightness,
        "requested_brightness": level,
        "fraction": args.fraction,
        "hold_ms": args.hold_ms,
        "temperatures_before": before_temperatures,
        "flash_subdevices": flash_subdevices(),
        "taint_before": before_taint,
    }
    error = None
    try:
        write_text(led / "brightness", "0")
        time.sleep(0.1)
        write_text(led / "brightness", str(level))
        time.sleep(args.hold_ms / 1000)
        result["brightness_on"] = read_text(led / "brightness")
        result["temperatures_on"] = thermal_snapshot()
    except Exception as exc:
        error = str(exc)
    finally:
        try:
            write_text(led / "brightness", "0")
        except Exception as exc:
            error = (error + "; " if error else "") + "cleanup: " + str(exc)
        time.sleep(0.15)

    v4l2_torch = {
        "attempted": False,
        "on": None,
        "off": None,
        "strobe_off": None,
        "intensity_ua": args.torch_intensity_ua,
        "error": None,
    }
    if result["flash_subdevices"]:
        device = result["flash_subdevices"][0]["device"]
        v4l2_torch["attempted"] = True
        try:
            intensity = v4l2_control(
                device,
                "intensity_torch_mode",
                str(args.torch_intensity_ua),
            )
            if intensity["returncode"] != 0:
                raise RuntimeError(
                    "set intensity_torch_mode: " + intensity["stderr"]
                )
            enabled = v4l2_control(device, "led_mode", "2")
            if enabled["returncode"] != 0:
                raise RuntimeError("set torch mode: " + enabled["stderr"])
            time.sleep(args.hold_ms / 1000)
            mode_on = v4l2_control(device, "led_mode")
            v4l2_torch["on"] = v4l2_control_value(mode_on)
        except Exception as exc:
            v4l2_torch["error"] = str(exc)
        finally:
            try:
                disabled = v4l2_control(device, "led_mode", "0")
                if disabled["returncode"] != 0:
                    v4l2_torch["error"] = (
                        "turn torch off: " + disabled["stderr"]
                    )
                off = v4l2_control(device, "led_mode")
                v4l2_torch["off"] = v4l2_control_value(off)
                strobe_off = v4l2_control(device, "strobe_status")
                v4l2_torch["strobe_off"] = (
                    v4l2_control_value(strobe_off) == 0
                )
            except Exception as exc:
                v4l2_torch["error"] = (
                    (v4l2_torch["error"] + "; " if v4l2_torch["error"] else "")
                    + "cleanup: " + str(exc)
                )

    result["brightness_off"] = read_text(led / "brightness")
    result["temperatures_after"] = thermal_snapshot()
    result["flash_subdevices_after"] = flash_subdevices()
    result["v4l2_torch"] = v4l2_torch
    after_dmesg = dmesg_tail()
    result["new_dmesg"] = [
        line for line in after_dmesg
        if line not in before_dmesg
    ]
    result["taint_after"] = read_text(Path("/proc/sys/kernel/tainted"))
    result["error"] = error
    v4l2_controls = [
        control
        for device in result["flash_subdevices_after"]
        for control in device["controls"].values()
    ]
    v4l2_queries_ok = bool(v4l2_controls) and all(
        device["controls"].keys() == {"strobe_status", "faults"}
        and all(
            control["returncode"] == 0
            and control["value"] is not None
            for control in device["controls"].values()
        )
        for device in result["flash_subdevices_after"]
    )
    v4l2_strobe_off = all(
        parse_control_integer(
            device["controls"].get("strobe_status", {}).get("value")
        ) == 0
        for device in result["flash_subdevices_after"]
    )
    v4l2_faults_clear = all(
        parse_control_integer(
            device["controls"].get("faults", {}).get("value")
        ) == 0
        for device in result["flash_subdevices_after"]
    )
    result["v4l2_queries_ok"] = v4l2_queries_ok
    result["v4l2_strobe_off"] = v4l2_strobe_off
    result["v4l2_faults_clear"] = v4l2_faults_clear
    v4l2_torch_ok = (
        v4l2_torch["attempted"]
        and v4l2_torch["error"] is None
        and v4l2_torch["on"] == 2
        and v4l2_torch["off"] == 0
        and v4l2_torch["strobe_off"] is True
    )
    result["v4l2_torch_ok"] = v4l2_torch_ok
    result["passed"] = (
        error is None
        and result["brightness_on"] == str(level)
        and result["brightness_off"] == "0"
        and result["taint_after"] == before_taint
        and v4l2_queries_ok
        and v4l2_strobe_off
        and v4l2_faults_clear
        and v4l2_torch_ok
    )

    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    sys.stdout.write(text)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
