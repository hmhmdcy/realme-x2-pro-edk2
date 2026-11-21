#!/usr/bin/env python3
"""Inspect a built rootfs without booting it.

Reads lib/apk/db/installed from an already-mounted root tree and reports the
packages the port depends on, plus the files its runtime scripts need.  The
goal is to catch "built but never installed" gaps before flashing.

Usage:
    inspect-rootfs.py --root /mnt/rootchk [--expect FILE]
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REQUIRED = [
    "libcamera", "libcamera-ipa", "libcamera-tools", "libcamera-gstreamer",
    "libcamera-v4l2", "samurai-camera-config", "samurai-camera-stack",
    "samurai-platform", "samurai-desktop", "mesa-vulkan-freedreno-samurai",
    "device-realme-samurai", "device-realme-samurai-kernel-none",
    "usb-signaller", "unudhcpd", "samurai-libssc", "samurai-hexagonrpcd",
    "samurai-radio-tools", "samurai-gnss-assist", "samurai-ssc",
    "samurai-openrc", "plasma-mobile", "openrc",
]

# Commands referenced by device/testing/samurai-platform runtime scripts.
REQUIRED_BINS = [
    "samurai-tqftpserv", "samurai-rmtfs-cow", "samurai-dms-mac-read",
    "samurai-bt-address", "samurai-wifi", "usb-signaller", "qrtr-lookup",
]

REQUIRED_PATHS = [
    "/usr/libexec/nfc/neard",
]

REQUIRED_MODULES = [
    "zram.ko", "btqca.ko", "hci_uart.ko", "socinfo.ko", "fastrpc.ko",
    "ipa.ko", "rmnet.ko", "system_heap.ko", "cma_heap.ko",
    "leds-qcom-flash.ko", "leds-qcom-lpg.ko",
    "qcom-pm8008.ko", "qcom-pm8008-regulator.ko", "i2c-qcom-cci.ko",
    "qcom-camss.ko", "s5kgw1.ko", "imx319.ko", "s5k3m5.ko", "imx471.ko",
]

# The embedded initramfs (/usr/sbin/samurai-rootfs) refuses to switch root
# unless these are present.  A missing marker looks exactly like "the port
# does not boot": the phone stays in the diagnostic ramdisk.
SWITCH_ROOT_MARKER = "/etc/samurai-rootfs-release"
EXPECTED_ROOTFS_ID = "ROOTFS_ID=samurai-f2fs-rootfs01"

# Rootfs NCM layering: usb-signaller owns the gadget, but nothing in the
# distro brings usb0 UP.  Without this board glue the host can send while the
# gadget receive queue is never filled (ReceivedBytes=0, carrier 0, no DHCP).
NCM_GLUE_SERVICE = "/etc/init.d/samurai-usb-network"
NCM_GLUE_WATCHDOG = "/usr/sbin/samurai-usb-network-watchdog"

# apk-tools 3 refuses to read the installed database if any record contains
# fields it cannot parse; the whole package manager then fails with
# "v2 database format error".  Hand-written records used during bring-up
# caused exactly that, so the check is now part of the boot gate.
APKDB_FORBIDDEN = {
    "P:samurai-ncm-fallback",
}


def read_installed(root: Path) -> dict[str, dict[str, str]]:
    path = root / "lib/apk/db/installed"
    if not path.is_file():
        raise SystemExit(f"missing apk database: {path}")
    records: dict[str, dict[str, str]] = {}
    for block in path.read_text(errors="replace").split("\n\n"):
        row: dict[str, str] = {}
        for line in block.splitlines():
            if len(line) > 2 and line[1] == ":":
                row[line[0]] = line[2:]
        if row.get("P"):
            records[row["P"]] = row
    return records


def service_command_exists(root: Path, init_script: Path, name: str) -> bool:
    """Return True when the init script's command= resolves inside the root."""
    command = None
    for line in init_script.read_text(errors="replace").splitlines():
        line = line.strip()
        if line.startswith("command="):
            command = line.split("=", 1)[1].strip().strip('"')
    if not command:
        print(f"  MISSING command= in {name}")
        return False
    if command.startswith("/"):
        return (root / command.lstrip("/")).is_file()
    return (init_script.parent / command).is_file()


def ownership_mismatches(root: Path) -> list[str]:
    """Compare on-disk ownership with the apk database contract.

    apk records intended owner/group/mode in the a: field.  Setgid helpers
    such as dbus-daemon-launch-helper must stay root:messagebus 4750: if a
    staging tree is chowned wholesale to root:root the file loses its group
    and D-Bus system service activation fails for every client.
    """
    database = root / "lib/apk/db/installed"
    if not database.is_file():
        return []
    problems: list[str] = []
    for block in database.read_text(errors="replace").split("\n\n"):
        directory = ""
        target = ""
        for line in block.splitlines():
            key, _, value = line.partition(":")
            if key == "F":
                directory = value
            elif key == "R":
                target = value if value.startswith("/") else f"{directory}/{value}"
            elif key == "a" and target:
                parts = value.split(":")
                if len(parts) != 3:
                    continue
                try:
                    uid = int(parts[0])
                    gid = int(parts[1])
                    mode = int(parts[2], 8)
                except ValueError:
                    continue
                disk = root / target.lstrip("/")
                if disk.is_symlink() or not disk.exists():
                    continue
                st = disk.lstat()
                have = (st.st_uid, st.st_gid, st.st_mode & 0o7777)
                if have != (uid, gid, mode):
                    problems.append(
                        f"/{target} is {have[0]}:{have[1]} {have[2]:04o}, "
                        f"apk database says {uid}:{gid} {mode:04o}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--kernel-release", default="")
    args = parser.parse_args()
    root: Path = args.root

    records = read_installed(root)
    problems: list[str] = []

    print(f"root: {root}")
    print(f"installed packages: {len(records)}")
    print()

    print("required packages:")
    for name in REQUIRED:
        row = records.get(name)
        if row:
            print(f"  OK      {name:38s} {row.get('V', '?')}")
        else:
            print(f"  MISSING {name}")
            problems.append(f"package {name}")

    print()
    print("required commands:")
    for command in REQUIRED_BINS:
        found = None
        for directory in ("usr/sbin", "usr/bin", "sbin", "bin"):
            if (root / directory / command).exists():
                found = f"/{directory}/{command}"
                break
        if found:
            print(f"  OK      {command:26s} {found}")
        else:
            print(f"  MISSING {command}")
            problems.append(f"command {command}")

    for rel_path in REQUIRED_PATHS:
        target = root / rel_path.lstrip("/")
        if target.exists():
            print(f"  OK      {rel_path}")
        else:
            print(f"  MISSING {rel_path}")
            problems.append(f"path {rel_path}")

    depends = records.get("samurai-platform", {}).get("D", "")
    print()
    print("samurai-platform depends:")
    print(f"  {depends}")

    print()
    print("switch_root preconditions:")
    marker = root / SWITCH_ROOT_MARKER.lstrip("/")
    if marker.is_file() and EXPECTED_ROOTFS_ID in marker.read_text(errors="replace"):
        print(f"  OK      {SWITCH_ROOT_MARKER}")
    else:
        print(f"  MISSING {SWITCH_ROOT_MARKER} ({EXPECTED_ROOTFS_ID})")
        problems.append(f"switch_root marker {SWITCH_ROOT_MARKER}")

    init_link = root / "sbin/init"
    init_target = None
    if init_link.is_symlink():
        target = Path(os.readlink(init_link))
        init_target = (root / target.as_posix().lstrip("/")) if target.is_absolute() else (init_link.parent / target)
    elif init_link.exists():
        init_target = init_link
    if init_target is not None and init_target.exists():
        print(f"  OK      /sbin/init -> {init_target}")
    else:
        print("  MISSING /sbin/init")
        problems.append("/sbin/init")

    inittab = root / "etc/inittab"
    if inittab.is_file() and "openrc" in inittab.read_text(errors="replace"):
        print("  OK      /etc/inittab runs OpenRC")
    else:
        print("  MISSING /etc/inittab with OpenRC")
        problems.append("/etc/inittab")

    modules_root = root / "lib/modules"
    if modules_root.is_dir() and any(modules_root.iterdir()):
        releases = sorted(p.name for p in modules_root.iterdir() if p.is_dir())
        for release in releases:
            depfile = modules_root / release / "modules.dep"
            state = "OK" if depfile.is_file() else "no modules.dep"
            print(f"  {state:7} kernel modules {release}")
            if not depfile.is_file():
                problems.append(f"modules.dep for {release}")
            if not args.kernel_release or release == args.kernel_release:
                ko_names = {p.name for p in (modules_root / release).rglob("*.ko*")}
                missing_kos = [m for m in REQUIRED_MODULES if m not in ko_names]
                if missing_kos:
                    print(f"  MISSING modules in {release}: {', '.join(missing_kos)}")
                    problems.append(f"missing modules in {release}: {', '.join(missing_kos)}")
                else:
                    print(f"  OK      required RMX1931 .ko modules present in {release}")
        if args.kernel_release and args.kernel_release not in releases:
            print(f"  MISMATCH expected kernel release {args.kernel_release}, found {releases}")
            problems.append(f"kernel release mismatch {args.kernel_release}")
    else:
        print("  MISSING kernel modules under /lib/modules")
        problems.append("kernel modules")

    # elogind configuration contract: /etc/elogind/logind.conf must set
    # HandlePowerKey=ignore, otherwise short-pressing Power shuts down.
    logind_files = [root / "etc/elogind/logind.conf"]
    logind_dir = root / "etc/elogind/logind.conf.d"
    if logind_dir.is_dir():
        logind_files.extend(sorted(logind_dir.glob("*.conf")))
    powerkey_ignored = any(
        f.is_file() and "HandlePowerKey=ignore" in f.read_text(errors="replace")
        for f in logind_files
    )
    if powerkey_ignored:
        print("  OK      /etc/elogind HandlePowerKey=ignore")
    else:
        print("  MISSING /etc/elogind/logind.conf HandlePowerKey=ignore")
        problems.append("elogind HandlePowerKey=ignore")

    # urfkilld defaults to key_control=true, which EVIOCGRABs /dev/input/event*.
    # On this handset the Wayland compositor owns the GPIO key device, so the
    # grab fails and urfkilld exits 1 -> OpenRC reports urfkill as failed.
    urfkill_conf = root / "etc/urfkill/urfkill.conf"
    if urfkill_conf.is_file():
        text = urfkill_conf.read_text(errors="replace")
        if "key_control=false" in text:
            print("  OK      /etc/urfkill key_control=false")
        elif "key_control=true" in text or "# key_control=true" in text:
            print("  BROKEN  /etc/urfkill still enables evdev key grab")
            problems.append("urfkill key_control")
    # /etc/urfkill/hardware.conf is generated by urfkilld on every start and
    # always reflects the profile defaults, so it is not the authority here;
    # the [general] key_control value above is what urfkilld actually loads.

    # apk records intended ownership; losing a setgid group breaks D-Bus
    # system service activation for every client on the image.
    ownership = ownership_mismatches(root)
    if ownership:
        print(f"  BROKEN  {len(ownership)} file(s) differ from apk ownership metadata")
        for item in ownership:
            print(f"          {item}")
            problems.append(f"ownership {item.split(' is ')[0]}")
    else:
        print("  OK      on-disk ownership matches apk database")

    # SLPI sensor lifecycle contract.
    ssc_bin = root / "usr/sbin/samurai-ssc"
    ssc_link = root / "etc/runlevels/default/samurai-ssc"
    if ssc_bin.is_file():
        if not ssc_link.is_symlink():
            print("  MISSING default runlevel link samurai-ssc")
            problems.append("samurai-ssc runlevel")
        elif "st_mode" not in ssc_bin.read_text(errors="replace"):
            print("  BROKEN  samurai-ssc lacks read-only sensor-power/state support")
            problems.append("samurai-ssc read-only sensor-power check")
        else:
            print("  OK      samurai-ssc enabled and rproc_subdev-compatible")

    # Rootfs NCM glue.  A correctly created gadget is not enough: usb0 has to
    # be brought UP before u_ether fills the RX queue and raises carrier.  The
    # initramfs did this unconditionally; the distro services do not.
    glue = root / NCM_GLUE_SERVICE.lstrip("/")
    watchdog = root / NCM_GLUE_WATCHDOG.lstrip("/")
    default_link = root / "etc/runlevels/default/samurai-usb-network"
    boot_link = root / "etc/runlevels/boot/samurai-ncm-fallback"
    if not glue.is_file():
        print(f"  MISSING {NCM_GLUE_SERVICE}")
        problems.append(f"NCM glue {NCM_GLUE_SERVICE}")
    elif not watchdog.is_file():
        print(f"  MISSING {NCM_GLUE_WATCHDOG}")
        problems.append(f"NCM glue {NCM_GLUE_WATCHDOG}")
    elif not service_command_exists(root, glue, "samurai-usb-network"):
        print("  BROKEN  samurai-usb-network command= path is missing")
        problems.append("samurai-usb-network command path")
    elif not default_link.is_symlink():
        print("  MISSING default runlevel link samurai-usb-network")
        problems.append("samurai-usb-network runlevel")
    elif boot_link.exists() or boot_link.is_symlink():
        print("  STALE   /etc/runlevels/boot/samurai-ncm-fallback")
        problems.append("stale samurai-ncm-fallback runlevel link")
    else:
        print(f"  OK      {NCM_GLUE_SERVICE} (default, supervised)")

    dhcp_te = root / "etc/init.d/unudhcpd.usb0"
    if dhcp_te.exists() or dhcp_te.is_symlink():
        print("  OK      /etc/init.d/unudhcpd.usb0")
    else:
        print("  MISSING /etc/init.d/unudhcpd.usb0 (template instance)")
        problems.append("unudhcpd.usb0 template")

    # Package database health: apk must be able to read it, otherwise no
    # further bootstrap or update is possible on the device.
    installed = root / "lib/apk/db/installed"
    for name in APKDB_FORBIDDEN:
        if installed.is_file() and (name + "\n") in installed.read_text(errors="replace"):
            print(f"  BROKEN  apk database still contains {name}")
            problems.append(f"apkdb record {name}")
    world = root / "etc/apk/world"
    if world.is_file() and world.read_text(errors="replace").strip():
        print("  OK      /etc/apk/world present")
    else:
        print("  MISSING /etc/apk/world")
        problems.append("etc/apk/world")

    version = None
    os_release = root / "etc/os-release"
    if os_release.is_file():
        for line in os_release.read_text(errors="replace").splitlines():
            if line.startswith("PRETTY_NAME="):
                version = line.split("=", 1)[1].strip('"')
    print()
    print(f"os-release: {version or 'absent'}")

    if problems:
        print()
        print("PROBLEMS:")
        for item in problems:
            print(f"  - {item}")
        return 1

    print()
    print("all required packages and commands present")
    return 0


if __name__ == "__main__":
    sys.exit(main())
