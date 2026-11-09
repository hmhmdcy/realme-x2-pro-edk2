#!/usr/bin/env python3
"""Verify the flashed v7.3.1 camera candidate and its standard interfaces."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


RELEASE = "7.3.1-rmx1931-samurai-v731"
BOOT_SHA256 = "9b9be136bd3ee2328f0c4273a829471ad0cd73a7fe7d718825ac024f7af3ae54"
IMAGE_SHA256 = "aa6c4b6b43ec45f4c41d3d420b980e35876860537cb6f2cb96ec5063aab8432a"
DTB_SHA256 = "3799ec6c7d3e0c67a657859a37b2fe147fa21a9dedc84d49c8eb83fd8debc805"
STANDARD_BOOT_SHA256 = (
    "e1cccd9d3d1119c2b40bda4d15834ea857ca8ec897e611f9af28b1e66050bd19"
)
STANDARD_IMAGE_SHA256 = (
    "5069b1b47d453b11f11ce4a831de6821971b064184452303d4373ae7c8fbd2bd"
)
USB_FIFO_BOOT_SHA256 = (
    "7f8d7a65a3c450fd6abd2a41c5d4e1f359ffe4f7b66a36e53e4ec7aea2782777"
)
USB_FIFO_DTB_SHA256 = (
    "c9f948cdac6e58b23ba5bd9bb29137d6266154ce22540fb4d585e24826649fc5"
)
CLOCK_BOOT_SHA256 = (
    "c5e856d5ac06a42fb55df909dae26fe26293517aa65fd67570730f6de068690c"
)
CLOCK_IMAGE_SHA256 = (
    "9d50f46424a64c9ce7ff5277ea2abab18480df1b23a78c7d2199a9bc261d925e"
)
FLASH_LED_V4L2_BOOT_SHA256 = (
    "5b4dd4871f6856710ff58e722ffd8b2c30d04baf0104b262adcb02e46a7651bf"
)
FLASH_LED_V4L2_IMAGE_SHA256 = IMAGE_SHA256
FLASH_LED_V4L2_DTB_SHA256 = (
    "b244b3f10a14811dca2e808efa8c840f432cac69020e66b60eba97d02794a18e"
)
THIN_PRIVATE_IMAGE_SHA256 = (
    "f8d8962197827dafbe50e551f5df03391c43ec0269449fa87b833e57799656a5"
)
STANDARD_CMDLINE = (
    "console=tty0 loglevel=4 panic=15 root=PARTLABEL=userdata "
    "rootfstype=f2fs rootwait rw clk_ignore_unused"
)
CLOCK_CMDLINE = (
    "console=tty0 loglevel=4 panic=15 root=PARTLABEL=userdata "
    "rootfstype=f2fs rootwait rw"
)
CAMSS_MODULE_SHA256 = (
    "d7b3649d956fbad7b3b447131c4ef129de32a23027d2b566f9a070c6c21bf631"
)
IMX471_MODULE_SHA256 = (
    "53ac75440404fd477aa6dc0751b58b9192a9af05ed545abe9eb15ff72e328425"
)
S5K3M5_MODULE_SHA256 = (
    "c65af58edc066fb4167cb0aee0b69b0b2e7061780671f5f873e594d7b30d0b99"
)
EXPECTED_MODULE_COUNT = 773
FLASH_LED_V4L2_MODULE_COUNT = 774
FLASH_LED_V4L2_CLASS_MODULE_SHA256 = (
    "4d89be85856854b404b220c19865b2392f0ce8462810e7566558b11b65581ab4"
)
FLASH_LED_QCOM_MODULE_SHA256 = (
    "fbc26126e885c5682c8d282b9657ed77c23098438c853eff6e36bb73876653b1"
)
BLUETOOTH_HOST_MODULE_HASHES = {
    "bnep": "aa2e7affa0bc7238a61a0bdfc190be533f6382ea21eaebf88b3419301a412b74",
    "uhid": "a5e72e3ed257c978e35fe12dcb18784d790f96c059c37cc09576b813d57ceea0",
    "uinput": "d5a94b699e33aef2835a0ba5e2f419574f7da3c643ade9d8f2ed4be781029bbb",
}
EXPECTED_NCM_QMULT = "20"
EXPECTED_CMDLINE = {
    "console=tty0",
    "loglevel=4",
    "panic=15",
    "clk_ignore_unused",
}
FORBIDDEN_CMDLINE_PREFIXES = (
    "ignore_loglevel",
    "pd_ignore_unused",
    "regulator_ignore_unused",
)
CLOCK_FORBIDDEN_CMDLINE_PREFIXES = (
    *FORBIDDEN_CMDLINE_PREFIXES,
    "clk_ignore_unused",
)
SENSOR_MODELS = ("imx471", "imx319", "s5k3m5", "s5kgw1")
CAMERAS = {
    "front": (1928, 1088, 2416, 5257216),
    "rear": (1632, 1224, 2048, 5013504),
    "tele": (2104, 1560, 2640, 8236800),
    "wide": (4608, 3456, 5760, 39813120),
}
PRIVATE_STATUS_DEVICE_NAMES = {"samurai-max98937", "samurai-aw8697"}
THERMAL_REQUIRED_ZONES = {
    "camera-thermal",
    "cpu0-thermal",
    "gpu-top-thermal",
    "modem-thermal",
    "pm8150-thermal",
    "pm8150b-thermal",
    "pm8150l-thermal",
    "wlan-thermal",
}


def command(argv, timeout=30):
    try:
        return subprocess.run(
            argv,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as error:
        return subprocess.CompletedProcess(argv, 127, str(error))


def read_text(path):
    try:
        return Path(path).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def read_nul_text(path):
    try:
        return (
            Path(path)
            .read_bytes()
            .replace(b"\0", b" ")
            .decode("utf-8", "replace")
            .strip()
        )
    except OSError:
        return ""


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def partition_by_name(name):
    link = Path("/dev/disk/by-partlabel") / name
    if link.exists():
        return link.resolve()
    for uevent in Path("/sys/class/block").glob("*/uevent"):
        lines = read_text(uevent).splitlines()
        if f"PARTNAME={name}" in lines:
            return Path("/dev") / uevent.parent.name
    return None


def mount_for(source):
    source = os.path.realpath(source)
    for line in Path("/proc/mounts").read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if len(fields) >= 2 and os.path.realpath(fields[0]) == source:
            return Path(fields[1].replace("\\040", " "))
    return None


def mount_fstype_for(source):
    source = os.path.realpath(source)
    for line in Path("/proc/mounts").read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if len(fields) >= 3 and os.path.realpath(fields[0]) == source:
            return fields[2]
    return ""


def kernel_mount(candidate):
    path = Path(candidate)
    if (path / "Image").is_file() and (path / "samurai.dtb").is_file():
        return path
    logdump = partition_by_name("logdump")
    if logdump:
        mounted = mount_for(logdump)
        if mounted and (mounted / "Image").is_file():
            return mounted
    return path


def mount_kernel_store(candidate):
    path = kernel_mount(candidate)
    if (path / "Image").is_file() and (path / "samurai.dtb").is_file():
        return path, False

    logdump = partition_by_name("logdump")
    if not logdump:
        return path, False
    mountpoint = Path("/tmp/samurai-v731-kernel-ro")
    mountpoint.mkdir(parents=True, exist_ok=True)
    mounted = command(["mountpoint", "-q", str(mountpoint)]).returncode == 0
    if not mounted:
        result = command(["mount", "-o", "ro", str(logdump), str(mountpoint)])
        mounted = result.returncode == 0
    return (mountpoint if mounted else path), mounted


def find_camss_media():
    for device in sorted(Path("/dev").glob("media*")):
        result = command(["media-ctl", "-d", str(device), "-p"])
        if result.returncode == 0 and "msm_vfe0_rdi0" in result.stdout:
            return device, result.stdout
    return None, ""


def display_state():
    for device in sorted(Path("/sys/class/drm").glob("card*-DSI-*")):
        status = read_text(device / "status")
        if status:
            return {
                "device": device.name,
                "status": status,
                "enabled": read_text(device / "enabled"),
                "dpms": read_text(device / "dpms"),
            }
    return {}


def thermal_state():
    root = Path("/sys/class/thermal")
    zone_paths = (
        sorted(root.glob("thermal_zone[0-9]*")) if root.is_dir() else []
    )
    cooling_paths = (
        sorted(root.glob("cooling_device[0-9]*")) if root.is_dir() else []
    )
    zones = []
    cooling = []
    for path in zone_paths:
        raw_temp = read_text(path / "temp")
        try:
            temp = int(raw_temp)
        except (TypeError, ValueError):
            temp = None
        trips = []
        indices = set()
        for item in path.glob("trip_point_*_temp"):
            match = re.fullmatch(r"trip_point_(\d+)_temp", item.name)
            if match:
                indices.add(int(match.group(1)))
        for index in sorted(indices):
            raw_trip = read_text(path / f"trip_point_{index}_temp")
            try:
                trip_temp = int(raw_trip)
            except (TypeError, ValueError):
                trip_temp = None
            trips.append({
                "index": index,
                "temp": trip_temp,
                "type": read_text(path / f"trip_point_{index}_type"),
            })
        zones.append({
            "path": str(path),
            "type": read_text(path / "type"),
            "temp": temp,
            "mode": read_text(path / "mode"),
            "policy": read_text(path / "policy"),
            "trips": trips,
        })
    for path in cooling_paths:
        cooling.append({
            "path": str(path),
            "type": read_text(path / "type"),
            "max_state": read_text(path / "max_state"),
            "current_state": read_text(path / "cur_state"),
        })
    types = {zone["type"] for zone in zones if zone["type"]}
    trip_types = {
        trip["type"]
        for zone in zones
        for trip in zone["trips"]
        if trip["type"]
    }
    temperatures = [
        zone["temp"] for zone in zones if zone["temp"] is not None
    ]
    return {
        "zones": zones,
        "cooling_devices": cooling,
        "zone_types": sorted(types),
        "trip_types": sorted(trip_types),
        "missing_required_zone_types": sorted(
            THERMAL_REQUIRED_ZONES - types
        ),
        "all_temperatures_readable": (
            bool(zones) and len(temperatures) == len(zones)
        ),
        "temperatures_plausible": bool(temperatures) and all(
            -40000 <= value <= 150000 for value in temperatures
        ),
    }


def flash_led_state(media_topology):
    led_root = Path("/sys/class/leds/white:flash")
    devices = []
    for path in sorted(Path("/dev").glob("v4l-subdev*")):
        result = command(
            ["v4l2-ctl", "-d", str(path), "--list-ctrls"],
            timeout=10,
        )
        if result.returncode != 0 or "led_mode" not in result.stdout:
            continue
        controls = {
            name: read_control(path, name)
            for name in ("led_mode", "intensity_torch_mode", "strobe_status", "faults")
        }
        devices.append({
            "device": str(path),
            "controls": controls,
        })
    return {
        "led_class_present": led_root.is_dir(),
        "led_max_brightness": read_text(led_root / "max_brightness"),
        "media_entity_present": "white:flash" in media_topology,
        "v4l2_subdevices": devices,
    }


def read_control(device, name):
    result = command(
        ["v4l2-ctl", "-d", str(device), f"--get-ctrl={name}"],
        timeout=10,
    )
    value = None
    match = re.search(r":\s*(-?\d+)", result.stdout)
    if match:
        value = int(match.group(1))
    return {
        "returncode": result.returncode,
        "value": value,
        "stdout": result.stdout.strip(),
    }


def wake_display():
    for line in command(["loginctl", "list-sessions", "--no-legend"]).stdout.splitlines():
        fields = line.split()
        if len(fields) < 3 or not fields[1].isdigit():
            continue
        user = fields[2]
        runtime = Path(f"/run/user/{fields[1]}")
        if not runtime.is_dir():
            continue
        displays = sorted(
            path.name
            for path in runtime.glob("wayland-*")
            if not path.name.endswith(".lock")
        )
        if not displays:
            continue
        result = command(
            [
                "runuser",
                "-u",
                user,
                "--",
                "env",
                f"XDG_RUNTIME_DIR={runtime}",
                f"WAYLAND_DISPLAY={displays[0]}",
                "/usr/sbin/kscreen-doctor",
                "--dpms",
                "on",
            ],
            timeout=20,
        )
        return {
            "attempted": True,
            "user": user,
            "wayland_display": displays[0],
            "returncode": result.returncode,
            "output": result.stdout.strip(),
        }
    return {"attempted": False}


def private_status_devices():
    devices = []
    root = Path("/sys/bus/i2c/devices")
    for device in sorted(root.glob("*")):
        name = read_text(device / "name")
        if name not in PRIVATE_STATUS_DEVICE_NAMES:
            continue
        driver = ""
        try:
            driver = (device / "driver").resolve().name
        except OSError:
            pass
        devices.append({
            "device": str(device),
            "name": name,
            "driver": driver,
            "status_present": (device / "status").exists(),
        })
    return devices


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--kernel-mount", default="/mnt/kernel")
    parser.add_argument("--scripts-dir", type=Path, default=Path(__file__).parent)
    parser.add_argument("--camera-dir", type=Path, default=Path("/tmp/samurai-camera-raw"))
    parser.add_argument("--skip-camera", action="store_true")
    parser.add_argument(
        "--standard-rootfs",
        action="store_true",
        help="Verify the paired no-diagnostic-initramfs direct-rootfs candidate.",
    )
    parser.add_argument(
        "--clock-rbcpr",
        action="store_true",
        help="Verify the clock RBCPR candidate without clk_ignore_unused.",
    )
    parser.add_argument(
        "--usb-fifo",
        action="store_true",
        help="Verify the standard-rootfs boot with the DWC3 TX FIFO DTB.",
    )
    parser.add_argument(
        "--flash-led-v4l2",
        action="store_true",
        help="Verify the deployed PM8150L flash-LED/V4L2 camera pair.",
    )
    parser.add_argument(
        "--thin-private",
        action="store_true",
        help="Verify the thin-private Image on the deployed flash/V4L2 FAT.",
    )
    parser.add_argument(
        "--bluetooth-host",
        action="store_true",
        help="Require the installed samurai-bluetooth-host module package.",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    profiles = [
        args.standard_rootfs,
        args.clock_rbcpr,
        args.usb_fifo,
        args.flash_led_v4l2,
        args.thin_private,
    ]
    if sum(profiles) > 1:
        parser.error("runtime profiles are mutually exclusive")
    rootfs_profile = any(profiles)
    if args.thin_private:
        expected_boot_hash = FLASH_LED_V4L2_BOOT_SHA256
        expected_image_hash = THIN_PRIVATE_IMAGE_SHA256
        expected_dtb_hash = FLASH_LED_V4L2_DTB_SHA256
        expected_module_count = FLASH_LED_V4L2_MODULE_COUNT
    elif args.flash_led_v4l2:
        expected_boot_hash = FLASH_LED_V4L2_BOOT_SHA256
        expected_image_hash = FLASH_LED_V4L2_IMAGE_SHA256
        expected_dtb_hash = FLASH_LED_V4L2_DTB_SHA256
        expected_module_count = FLASH_LED_V4L2_MODULE_COUNT
    elif args.usb_fifo:
        expected_boot_hash = USB_FIFO_BOOT_SHA256
        expected_image_hash = STANDARD_IMAGE_SHA256
        expected_dtb_hash = USB_FIFO_DTB_SHA256
        expected_module_count = EXPECTED_MODULE_COUNT
    elif args.standard_rootfs:
        expected_boot_hash = STANDARD_BOOT_SHA256
        expected_image_hash = STANDARD_IMAGE_SHA256
        expected_dtb_hash = DTB_SHA256
        expected_module_count = EXPECTED_MODULE_COUNT
    elif args.clock_rbcpr:
        expected_boot_hash = CLOCK_BOOT_SHA256
        expected_image_hash = CLOCK_IMAGE_SHA256
        expected_dtb_hash = DTB_SHA256
        expected_module_count = EXPECTED_MODULE_COUNT
    else:
        expected_boot_hash = BOOT_SHA256
        expected_image_hash = IMAGE_SHA256
        expected_dtb_hash = DTB_SHA256
        expected_module_count = EXPECTED_MODULE_COUNT
    if args.bluetooth_host:
        expected_module_count += len(BLUETOOTH_HOST_MODULE_HASHES)

    failures = []
    checks = {}
    warnings = []

    def check(name, condition, detail=""):
        checks[name] = bool(condition)
        if not condition:
            failures.append({"check": name, "detail": detail})

    release = os.uname().release
    boot_id = read_text("/proc/sys/kernel/random/boot_id")
    cmdline = read_text("/proc/cmdline")
    cmdline_tokens = set(cmdline.split())
    taint = read_text("/proc/sys/kernel/tainted")
    uptime = read_text("/proc/uptime").split()[0]

    check("release", release == RELEASE, release)
    check("boot_id_present", bool(boot_id), boot_id)
    if args.standard_rootfs or args.usb_fifo:
        check("cmdline_exact", cmdline == STANDARD_CMDLINE, cmdline)
    elif args.clock_rbcpr:
        check("cmdline_exact", cmdline == CLOCK_CMDLINE, cmdline)
    else:
        check(
            "cmdline_required",
            EXPECTED_CMDLINE.issubset(cmdline_tokens),
            cmdline,
        )
    if args.usb_fifo:
        fdt = Path("/sys/firmware/fdt")
        fdt_bytes = fdt.read_bytes() if fdt.is_file() else b""
        check("usb_txfifo_property", b"tx-fifo-resize\0" in fdt_bytes)
    forbidden_prefixes = (
        CLOCK_FORBIDDEN_CMDLINE_PREFIXES
        if args.clock_rbcpr
        else FORBIDDEN_CMDLINE_PREFIXES
    )
    forbidden = sorted(
        token
        for token in cmdline_tokens
        if any(
            token == prefix or token.startswith(prefix + "=")
            for prefix in forbidden_prefixes
        )
    )
    check("cmdline_constraints_removed", not forbidden, ",".join(forbidden))
    check("taint_zero", taint == "0", taint)

    private_devices = private_status_devices()
    if args.thin_private:
        by_name = {
            name: [item for item in private_devices if item["name"] == name]
            for name in PRIVATE_STATUS_DEVICE_NAMES
        }
        check(
            "thin_private_max98937_instances",
            len(by_name["samurai-max98937"]) == 2,
            json.dumps(by_name["samurai-max98937"]),
        )
        check(
            "thin_private_aw8697_instances",
            len(by_name["samurai-aw8697"]) == 1,
            json.dumps(by_name["samurai-aw8697"]),
        )
        check(
            "thin_private_status_absent",
            not any(item["status_present"] for item in private_devices),
            json.dumps(private_devices),
        )
        check(
            "standard_alsa_cards",
            "Realme X2 Pro" in read_text("/proc/asound/cards"),
            read_text("/proc/asound/cards"),
        )
        check(
            "standard_alsa_playback",
            command(["aplay", "-l"]).returncode == 0,
        )
        check(
            "standard_alsa_capture",
            command(["arecord", "-l"]).returncode == 0,
        )
        aw8697_input = []
        for device in sorted(Path("/sys/class/input").glob("event*")):
            if "AW8697 haptics" in read_text(device / "device/name"):
                aw8697_input.append({
                    "event": device.name,
                    "name": read_text(device / "device/name"),
                    "ff_capabilities": read_text(
                        device / "device/capabilities/ff"
                    ),
                })
        check(
            "standard_aw8697_input_ff",
            any(item["ff_capabilities"] for item in aw8697_input),
            json.dumps(aw8697_input),
        )

    boot_partition = partition_by_name("boot")
    check("boot_partition_found", boot_partition is not None)
    boot_hash = sha256_file(boot_partition) if boot_partition else ""
    check("boot_partition_hash", boot_hash == expected_boot_hash, boot_hash)

    root_mount = None
    root_fstype = ""
    pid1_cmdline = ""
    if rootfs_profile:
        userdata = partition_by_name("userdata")
        check("root_partition_found", userdata is not None, str(userdata or ""))
        root_mount = mount_for(userdata) if userdata else None
        root_fstype = mount_fstype_for(userdata) if userdata else ""
        check("root_mounted", root_mount == Path("/"), str(root_mount or ""))
        check("root_fstype_f2fs", root_fstype == "f2fs", root_fstype)
        pid1_cmdline = read_nul_text("/proc/1/cmdline")
        check(
            "pid1_from_rootfs",
            pid1_cmdline.startswith("/sbin/init"),
            pid1_cmdline,
        )

    kernel_store, kernel_store_mounted = mount_kernel_store(args.kernel_mount)
    image = kernel_store / "Image"
    dtb = kernel_store / "samurai.dtb"
    check("kernel_image_present", image.is_file(), str(image))
    check("kernel_dtb_present", dtb.is_file(), str(dtb))
    image_hash = sha256_file(image) if image.is_file() else ""
    dtb_hash = sha256_file(dtb) if dtb.is_file() else ""
    check("kernel_image_hash", image_hash == expected_image_hash, image_hash)
    check("kernel_dtb_hash", dtb_hash == expected_dtb_hash, dtb_hash)
    if kernel_store_mounted:
        command(["umount", str(kernel_store)])

    module_root = Path("/lib/modules") / release
    release_modules = sorted(module_root.rglob("*.ko")) if module_root.is_dir() else []
    check("module_root_present", module_root.is_dir(), str(module_root))
    check(
        "module_count",
        len(release_modules) == expected_module_count,
        str(len(release_modules)),
    )
    check(
        "release_modules_layout",
        all(
            module.relative_to(module_root).parts[0] == "kernel"
            for module in release_modules
        ),
    )
    check("no_updates_modules", not (module_root / "updates").exists())
    camss_modules = list(module_root.rglob("qcom-camss.ko"))
    camss_module_hash = sha256_file(camss_modules[0]) if camss_modules else ""
    check(
        "camss_module_hash",
        camss_module_hash == CAMSS_MODULE_SHA256,
        camss_module_hash,
    )
    sensor_module_hashes = {}
    for name, expected in (
        ("imx471", IMX471_MODULE_SHA256),
        ("s5k3m5", S5K3M5_MODULE_SHA256),
    ):
        modules = [module for module in release_modules if module.name == f"{name}.ko"]
        digest = sha256_file(modules[0]) if modules else ""
        sensor_module_hashes[name] = digest
        check(
            f"{name}_module_hash",
            digest == expected,
            digest,
        )
    flash_module_hashes = {}
    if args.flash_led_v4l2:
        for name, expected in (
            ("v4l2-flash-led-class", FLASH_LED_V4L2_CLASS_MODULE_SHA256),
            ("leds-qcom-flash", FLASH_LED_QCOM_MODULE_SHA256),
        ):
            modules = [
                module for module in release_modules if module.name == f"{name}.ko"
            ]
            digest = sha256_file(modules[0]) if modules else ""
            flash_module_hashes[name] = digest
            check(
                f"{name}_module_hash",
                digest == expected,
                digest,
            )
    bluetooth_host_module_hashes = {}
    if args.bluetooth_host:
        for name, expected in BLUETOOTH_HOST_MODULE_HASHES.items():
            modules = [
                module for module in release_modules if module.name == f"{name}.ko"
            ]
            digest = sha256_file(modules[0]) if modules else ""
            bluetooth_host_module_hashes[name] = digest
            check(
                f"bluetooth_host_{name}_module_hash",
                digest == expected,
                digest,
            )
        check(
            "bluetooth_host_modules_loaded",
            all(
                Path(f"/sys/module/{name}").is_dir()
                for name in BLUETOOTH_HOST_MODULE_HASHES
            ),
        )
        check(
            "bluetooth_host_uhid",
            Path("/dev/uhid").is_char_device(),
        )
        check(
            "bluetooth_host_uinput",
            Path("/dev/uinput").is_char_device(),
        )

    media, media_topology = find_camss_media()
    check("camss_media_device", media is not None, str(media or ""))
    entities = {
        model: model in media_topology
        for model in (*SENSOR_MODELS, "lc898219xi", "msm_csiphy", "msm_csid")
    }
    for entity, present in entities.items():
        check(f"media_entity_{entity}", present)

    flash_led = flash_led_state(media_topology)
    if args.flash_led_v4l2:
        check(
            "flash_led_class_present",
            flash_led["led_class_present"],
            str(flash_led["led_class_present"]),
        )
        check(
            "flash_led_media_entity",
            flash_led["media_entity_present"],
            str(flash_led["media_entity_present"]),
        )
        check(
            "flash_led_v4l2_subdevice",
            bool(flash_led["v4l2_subdevices"]),
            str(len(flash_led["v4l2_subdevices"])),
        )
        check(
            "flash_led_v4l2_controls",
            bool(flash_led["v4l2_subdevices"])
            and all(
                control["returncode"] == 0 and control["value"] is not None
                for device in flash_led["v4l2_subdevices"]
                for control in device["controls"].values()
            ),
        )
        check(
            "flash_led_idle_strobe",
            bool(flash_led["v4l2_subdevices"])
            and all(
                device["controls"]["strobe_status"]["value"] == 0
                for device in flash_led["v4l2_subdevices"]
            ),
        )

    video = None
    if media:
        result = command(["media-ctl", "-d", str(media), "-e", "msm_vfe0_video0"])
        video = result.stdout.strip().strip('"')
        if result.returncode != 0:
            errors = [
                candidate
                for candidate in media_topology.splitlines()
                if "msm_vfe0_rdi0" in candidate and "/dev/video" in candidate
            ]
            if errors:
                video = re.search(r"/dev/video\d+", errors[0]).group(0)
    check("camss_video_node", bool(video and Path(video).exists()), video or "")

    camss_status = read_text(
        "/sys/bus/platform/devices/acb3000.camss/power/runtime_status"
    )
    mmcx_state = read_text("/sys/kernel/debug/pm_genpd/mmcx/current_state")
    mmcx_perf = read_text("/sys/kernel/debug/pm_genpd/mmcx/perf_state")
    check("camss_idle", camss_status == "suspended", camss_status)
    check(
        "mmcx_idle",
        mmcx_perf in {"64", "128"},
        f"{mmcx_state}/{mmcx_perf}",
    )

    clock_rbcpr = {}
    if args.clock_rbcpr:
        clock_root = Path("/sys/kernel/debug/clk/gcc_cpuss_rbcpr_clk")
        clock_rbcpr = {
            "flags": read_text(clock_root / "clk_flags"),
            "prepare_count": read_text(clock_root / "clk_prepare_count"),
            "enable_count": read_text(clock_root / "clk_enable_count"),
            "rate": read_text(clock_root / "clk_rate"),
        }
        check(
            "clock_rbcpr_critical_flag",
            "CLK_IS_CRITICAL" in clock_rbcpr["flags"].splitlines(),
            clock_rbcpr["flags"],
        )
        check(
            "clock_rbcpr_prepared",
            clock_rbcpr["prepare_count"] == "1",
            clock_rbcpr["prepare_count"],
        )
        check(
            "clock_rbcpr_enabled",
            clock_rbcpr["enable_count"] == "1",
            clock_rbcpr["enable_count"],
        )
        clock_summary = read_text("/sys/kernel/debug/clk/clk_summary")
        clock_line = next(
            (
                line
                for line in clock_summary.splitlines()
                if line.split() and line.split()[0] == "gcc_cpuss_rbcpr_clk"
            ),
            "",
        )
        clock_fields = clock_line.split()
        clock_rbcpr["summary_line"] = clock_line
        check("clock_rbcpr_summary_present", bool(clock_fields), clock_line)
        check(
            "clock_rbcpr_summary_counts",
            len(clock_fields) >= 9
            and clock_fields[1:3] == ["1", "1"]
            and clock_fields[8] == "Y",
            clock_line,
        )

    sensor_power = read_text("/sys/devices/platform/sensor-power/state")
    check("sensor_power_rails", sensor_power == "vdd=1 vddio=1", sensor_power)

    power_supply_root = Path("/sys/class/power_supply")
    power_supplies = (
        {path.name for path in power_supply_root.iterdir()}
        if power_supply_root.is_dir()
        else set()
    )
    check("fuel_gauge_bound", "bq28z610-0" in power_supplies)
    check("charger_bound", "mp2650-input" in power_supplies)
    check("nfc_controller_bound", Path("/sys/class/nfc/nfc0").exists())

    thermal = thermal_state()
    check(
        "thermal_zone_count",
        len(thermal["zones"]) >= 20,
        str(len(thermal["zones"])),
    )
    check(
        "thermal_required_zones",
        not thermal["missing_required_zone_types"],
        json.dumps(thermal["missing_required_zone_types"]),
    )
    check(
        "thermal_temperatures_readable",
        thermal["all_temperatures_readable"],
    )
    check(
        "thermal_temperatures_plausible",
        thermal["temperatures_plausible"],
    )
    check(
        "thermal_critical_trip",
        "critical" in thermal["trip_types"],
        json.dumps(thermal["trip_types"]),
    )
    check(
        "thermal_cooling_device",
        bool(thermal["cooling_devices"]),
        str(len(thermal["cooling_devices"])),
    )
    check(
        "thermal_cpu_cooling_device",
        any(
            "cpu" in (device["type"] or "").lower()
            or "cpufreq" in (device["type"] or "").lower()
            for device in thermal["cooling_devices"]
        ),
        json.dumps([
            device["type"] for device in thermal["cooling_devices"]
        ]),
    )

    udc_root = Path("/sys/class/udc")
    udc = (
        {
            device.name: read_text(device / "state")
            for device in sorted(udc_root.iterdir())
        }
        if udc_root.is_dir()
        else {}
    )
    check("udc_configured", "configured" in udc.values(), json.dumps(udc))
    ncm_qmult = read_text(
        "/sys/kernel/config/usb_gadget/samurai/functions/ncm.usb0/qmult"
    )
    usb0_carrier = read_text("/sys/class/net/usb0/carrier")
    check("ncm_qmult", ncm_qmult == EXPECTED_NCM_QMULT, ncm_qmult)
    check("usb0_carrier", usb0_carrier == "1", usb0_carrier)

    dsi = display_state()
    display_wake = {"attempted": False}
    if dsi.get("dpms") != "On":
        display_wake = wake_display()
        if display_wake.get("returncode") == 0:
            time.sleep(3)
            dsi = display_state()
    check("dsi_connected", dsi.get("status") == "connected", json.dumps(dsi))
    if dsi.get("enabled") != "enabled" or dsi.get("dpms") != "On":
        warnings.append("DSI is connected but the compositor left it powered off")

    wireless = [
        path.name
        for path in Path("/sys/class/net").iterdir()
        if (path / "wireless").exists()
    ]
    route = command(["ip", "-4", "route", "show", "default"])
    route_text = route.stdout.strip()
    check("wifi_interface", bool(wireless), ",".join(sorted(wireless)))
    check(
        "wifi_default_route",
        bool(wireless) and any(name in route_text for name in wireless),
        route_text,
    )

    services = {
        name: command(["rc-service", name, "status"]).returncode
        for name in ("sshd", "tinydm", "samurai-usb", "sleep-inhibitor")
    }
    for name, returncode in services.items():
        check(f"service_{name}", returncode == 0, str(returncode))
    check(
        "kwin_running",
        command(["pgrep", "-x", "kwin_wayland"]).returncode == 0,
    )
    check(
        "plasmashell_running",
        command(["pgrep", "-x", "plasmashell"]).returncode == 0,
    )

    boot_dmesg = command(["dmesg"], timeout=60).stdout
    rpmh_ret_95 = len(re.findall(r"RPMh.*ret=-95", boot_dmesg))
    if rpmh_ret_95:
        warnings.append("RPMh ret=-95 diagnostics are still present")
    boot_warnings = len(re.findall(r"\bWARNING:", boot_dmesg))

    camera_result = {"ran": False}
    runtime_faults = {}
    if not args.skip_camera:
        camera_list = command(["cam", "-l"], timeout=60)
        camera_list_errors = re.findall(
            r"Unable to get rectangle .*",
            camera_list.stdout,
        )
        check(
            "libcamera_list_exit",
            camera_list.returncode == 0,
            str(camera_list.returncode),
        )
        check(
            "libcamera_no_selection_errors",
            not camera_list_errors,
            json.dumps(camera_list_errors),
        )
        capture = command(
            [
                "sh",
                str(args.scripts_dir / "test-camera-four-raw.sh"),
                "all",
                str(args.camera_dir),
            ],
            timeout=240,
        )
        check("camera_capture_exit", capture.returncode == 0, str(capture.returncode))
        captured = {
            name: int(size)
            for name, size in re.findall(
                r"^RESULT (\w+) bytes=(\d+)$", capture.stdout, re.MULTILINE
            )
        }
        for name, (_, _, _, expected_bytes) in CAMERAS.items():
            check(
                f"camera_bytes_{name}",
                captured.get(name) == expected_bytes,
                str(captured.get(name)),
            )

        verify = command(
            [
                sys.executable,
                str(args.scripts_dir / "verify-camera-raw.py"),
                str(args.camera_dir),
            ],
            timeout=360,
        )
        verified = {}
        if verify.returncode == 0:
            try:
                verified = json.loads(verify.stdout)
            except json.JSONDecodeError:
                verified = {}
        check("camera_raw_verify_exit", verify.returncode == 0, str(verify.returncode))
        for name, (width, height, stride, expected_bytes) in CAMERAS.items():
            result = verified.get(name, {})
            public_result = {
                "bytes": result.get("bytes"),
                "width": result.get("width"),
                "height": result.get("height"),
                "stride": result.get("stride"),
                "frame_diff_percent": result.get("frame_diff_percent"),
                "frames": result.get("frames", []),
            }
            camera_result[name] = public_result
            frames = result.get("frames", [])
            check(
                f"camera_shape_{name}",
                (result.get("width"), result.get("height"), result.get("stride"))
                == (width, height, stride),
            )
            check(
                f"camera_complete_{name}",
                result.get("bytes") == expected_bytes,
            )
            check(f"camera_two_frames_{name}", len(frames) == 2)
            check(
                f"camera_frames_nonzero_{name}",
                len(frames) == 2
                and all(frame.get("nonzero_percent") == 100.0 for frame in frames),
            )
            check(
                f"camera_frames_unsaturated_{name}",
                len(frames) == 2
                and all(frame.get("saturated_percent") == 0.0 for frame in frames),
            )
            check(
                f"camera_frames_changed_{name}",
                float(result.get("frame_diff_percent") or 0) > 0,
            )

        camera_dmesg = command(["dmesg"], timeout=60).stdout
        fault_patterns = {
            "oops": r"\bOops\b",
            "bug": r"\bBUG:",
            "panic": r"Kernel panic",
            "serror": r"\bSERROR\b",
            "call_trace": r"Call trace:",
            "gpu_fault": r"GPU fault|VM_BIND|VK_ERROR_DEVICE_LOST|arm_lpae_unmap",
        }
        runtime_faults = {
            name: len(re.findall(pattern, camera_dmesg))
            for name, pattern in fault_patterns.items()
        }
        check(
            "camera_no_kernel_fault",
            all(count == 0 for count in runtime_faults.values()),
            json.dumps(runtime_faults),
        )
        check(
            "taint_zero_after_camera",
            read_text("/proc/sys/kernel/tainted") == "0",
        )
        check(
            "camss_idle_after_camera",
            read_text(
                "/sys/bus/platform/devices/acb3000.camss/power/runtime_status"
            )
            == "suspended",
        )
        check(
            "mmcx_idle_after_camera",
            read_text("/sys/kernel/debug/pm_genpd/mmcx/perf_state") in {"64", "128"},
        )
        camera_result["ran"] = True

    report = {
        "schema": "samurai-v731-final-runtime-v1",
        "profile": (
            "thin-private"
            if args.thin_private
            else "flash-led-v4l2"
            if args.flash_led_v4l2
            else "clock-rbcpr"
            if args.clock_rbcpr
            else "usb-fifo-standard-rootfs"
            if args.usb_fifo
            else "standard-rootfs"
            if args.standard_rootfs
            else "camera"
        ),
        "passed": not failures,
        "collected_at_utc": datetime.now(timezone.utc).isoformat(),
        "boot_id": boot_id,
        "release": release,
        "uptime_seconds": float(uptime) if uptime else None,
        "cmdline": cmdline,
        "tainted": int(taint) if taint.isdigit() else taint,
        "hashes": {
            "boot_partition": boot_hash,
            "Image": image_hash,
            "samurai.dtb": dtb_hash,
            "qcom-camss.ko": camss_module_hash,
            "imx471.ko": sensor_module_hashes["imx471"],
            "s5k3m5.ko": sensor_module_hashes["s5k3m5"],
            "v4l2-flash-led-class.ko": flash_module_hashes.get(
                "v4l2-flash-led-class"
            ),
            "leds-qcom-flash.ko": flash_module_hashes.get("leds-qcom-flash"),
            **{
                f"{name}.ko": digest
                for name, digest in bluetooth_host_module_hashes.items()
            },
        },
        "root": {
            "mount": str(root_mount) if root_mount else None,
            "fstype": root_fstype,
            "pid1_cmdline": pid1_cmdline,
        }
        if rootfs_profile
        else {},
        "kernel_mount": str(kernel_store),
        "module_count": len(release_modules),
        "media": {
            "device": str(media) if media else None,
            "video": video,
            "entities": entities,
        },
        "runtime_pm": {
            "camss": camss_status,
            "mmcx_state": mmcx_state,
            "mmcx_perf": mmcx_perf,
        },
        "clock_rbcpr": clock_rbcpr,
        "thermal": thermal,
        "private_status_devices": private_devices,
        "flash_led": flash_led,
        "display": dsi,
        "display_wake": display_wake,
        "wireless": sorted(wireless),
        "udc": udc,
        "usb_ncm": {
            "qmult": ncm_qmult,
            "usb0_carrier": usb0_carrier,
        },
        "services": services,
        "boot_diagnostics": {
            "warning_lines": boot_warnings,
            "rpmh_ret_95_present": bool(rpmh_ret_95),
        },
        "camera": camera_result,
        "runtime_faults": runtime_faults,
        "checks": checks,
        "warnings": warnings,
        "failures": failures,
    }

    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    sys.stdout.write(rendered)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
