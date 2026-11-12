#!/usr/bin/env python3
"""Build and sign the board packages that own the current deployed files."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import stat
import subprocess

REPO = Path(__file__).resolve().parents[2]
PACKAGES = REPO / "linux-port/packages"
RELEASE = "7.3.0-rc6-rmx1931-samurai-k363+"
MODULE_ROOT = f"lib/modules/{RELEASE}/extra/samurai-charging"
SOURCE_DATE_EPOCH = 1793836800

parser = argparse.ArgumentParser()
parser.add_argument("--apk", required=True, type=Path)
parser.add_argument("--sign-key", required=True, type=Path)
parser.add_argument("--trusted-keys", required=True, type=Path)
parser.add_argument("--build-root", required=True, type=Path)
parser.add_argument("--output", required=True, type=Path)
args = parser.parse_args()

assert args.apk.is_file()
assert args.sign_key.is_file()
assert args.trusted_keys.is_dir()
assert args.build_root.is_absolute() and not args.build_root.exists()
assert not str(args.build_root).startswith("/mnt/")
args.build_root.mkdir(mode=0o700, parents=True)
args.output.mkdir(mode=0o700, parents=True, exist_ok=True)

records = []


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command, label):
    result = subprocess.run(
        [str(item) for item in command], capture_output=True)
    (args.build_root / (label + ".log")).write_bytes(
        result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError(label + " failed; inspect its build log")


def copy_file(source, target, mode, text=True):
    data = source.read_bytes()
    if text:
        data = data.replace(b"\r\n", b"\n")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    target.chmod(mode)


def normalize(root):
    for path in [*root.rglob("*"), root]:
        if not path.is_symlink():
            os.chown(path, 0, 0)
        os.utime(path, (SOURCE_DATE_EPOCH, SOURCE_DATE_EPOCH),
                 follow_symlinks=False)


def file_manifest(root):
    result = {}
    for path in sorted(root.rglob("*")):
        relative = str(path.relative_to(root))
        if path.is_symlink():
            result[relative] = {
                "kind": "symlink", "target": str(path.readlink())}
        elif path.is_file():
            result[relative] = {
                "kind": "file",
                "sha256": sha256(path),
                "mode": stat.S_IMODE(path.stat().st_mode),
            }
    return result


def make_package(name, version, arch, root, info, scripts=None):
    normalize(root)
    target = args.output / f"{name}-{version}.apk"
    assert not target.exists(), target
    metadata = {
        "name": name,
        "version": version,
        "arch": arch,
        "build-time": str(SOURCE_DATE_EPOCH),
        "maintainer": "Realme X2 Pro Linux port",
        **info,
    }
    command = [
        args.apk, "mkpkg", "--compat", "3.0.0",
        "--compression", "deflate:9",
        "--files", root,
        "--sign-key", args.sign_key,
        "--output", target,
    ]
    for key, value in sorted(metadata.items()):
        if value:
            command += ["--info", key + ":" + value]
    for kind, path in (scripts or {}).items():
        command += ["--script", kind + ":" + str(path)]
    run(command, name + "-mkpkg")
    run([args.apk, "--keys-dir", args.trusted_keys, "verify", target],
        name + "-verify")
    records.append({
        "name": name,
        "version": version,
        "arch": arch,
        "sha256": sha256(target),
        "bytes": target.stat().st_size,
        "files": file_manifest(root),
        "metadata": metadata,
    })


charging = args.build_root / "samurai-charging"
charging_source = PACKAGES / "samurai-charging"
copy_file(charging_source / "samurai-charging",
          charging / "usr/sbin/samurai-charging", 0o755)
copy_file(charging_source / "samurai-charging.initd",
          charging / "etc/init.d/samurai-charging", 0o755)
for module in ("samurai-mp2650", "samurai-usb-input",
               "samurai-gauge-protection"):
    copy_file(charging_source / "artifacts" / (module + ".ko"),
              charging / MODULE_ROOT / (module + ".ko"), 0o644, text=False)

manifest = json.loads(
    (charging_source / "installed-manifest.json").read_text())
for path in manifest["installed_files"]:
    staged = charging / path.lstrip("/")
    assert staged.is_file(), staged
    manifest["installed_files"][path] = sha256(staged)
manifest_target = charging / "usr/share/samurai-charging/manifest.json"
copy_file(charging_source / "installed-manifest.json",
          manifest_target, 0o644)
manifest_target.write_text(json.dumps(manifest, indent=2) + "\n")
make_package(
    "samurai-charging", "0.1.0-r2", "aarch64", charging,
    {
        "description": "Legacy Realme X2 Pro managed MP2650 charging experiment",
        "license": "LicenseRef-Local-Project",
        "origin": "samurai-charging",
        "url": "https://github.com/hmhmdcy/edk2-realme-x2-pro",
        "depends": "kmod python3 openrc",
    },
    {"post-install": charging_source / "samurai-charging.post-install"})

platform = args.build_root / "samurai-platform"
platform_source = PACKAGES / "samurai-platform"
platform_files = [
    ("usr_libexec_samurai-audio-route", "usr/libexec/samurai-audio-route", 0o755),
    ("usr_sbin_samurai-bluetooth", "usr/sbin/samurai-bluetooth", 0o755),
    ("usr_sbin_samurai-modem-configs", "usr/sbin/samurai-modem-configs", 0o755),
    ("usr_sbin_samurai-modem-remoteproc", "usr/sbin/samurai-modem-remoteproc", 0o755),
    ("usr_sbin_samurai-radio-address", "usr/sbin/samurai-radio-address", 0o755),
    ("usr_sbin_samurai-udhcpc-wlan", "usr/sbin/samurai-udhcpc-wlan", 0o755),
    ("usr_sbin_samurai-wifi", "usr/sbin/samurai-wifi", 0o755),
    ("usr_sbin_samurai-usb", "usr/sbin/samurai-usb", 0o755),
    ("usr_sbin_samurai-usb-recover", "usr/sbin/samurai-usb-recover", 0o755),
    ("etc_init.d_samurai-loopback", "etc/init.d/samurai-loopback", 0o755),
    ("etc_init.d_samurai-radio", "etc/init.d/samurai-radio", 0o755),
    ("etc_init.d_samurai-usb", "etc/init.d/samurai-usb", 0o755),
    ("etc_init.d_samurai-usb-recover", "etc/init.d/samurai-usb-recover", 0o755),
    ("etc_samurai_usb-dhcp.conf", "etc/samurai/usb-dhcp.conf", 0o644),
    ("etc_NetworkManager_conf.d_20-samurai-wlan.conf", "etc/NetworkManager/conf.d/20-samurai-wlan.conf", 0o644),
    ("etc_usb-signaller.d_90-samurai.toml", "etc/usb-signaller.d/90-samurai.toml", 0o644),
    ("etc_unudhcpd.conf", "etc/unudhcpd.conf", 0o644),
    ("etc_conf.d_unudhcpd", "etc/conf.d/unudhcpd", 0o644),
    ("usr_local_share_dbus-1_system-services_org.freedesktop.ModemManager1.service", "usr/local/share/dbus-1/system-services/org.freedesktop.ModemManager1.service", 0o644),
    ("99-realme-rmx1931-sensors.rules", "usr/lib/udev/rules.d/99-realme-rmx1931-sensors.rules", 0o644),
    ("99-realme-rmx1931-haptics.rules", "usr/lib/udev/rules.d/99-realme-rmx1931-haptics.rules", 0o644),
    ("usr_share_alsa_ucm2_conf.d_Realme_X2_Pro_HiFi.conf", "usr/share/alsa/ucm2/conf.d/Realme_X2_Pro/HiFi.conf", 0o644),
    ("usr_share_alsa_ucm2_conf.d_Realme_X2_Pro_Realme_X2_Pro.conf", "usr/share/alsa/ucm2/conf.d/Realme_X2_Pro/Realme_X2_Pro.conf", 0o644),
]
for source, target, mode in platform_files:
    copy_file(platform_source / source, platform / target, mode)
make_package(
    "samurai-platform", "6-r7", "noarch", platform,
    {
        "description": "Realme X2 Pro board-level platform and services",
        "license": "LicenseRef-Local-Project",
        "origin": "samurai-platform",
        "url": "https://github.com/hmhmdcy/edk2-realme-x2-pro",
        "depends": (
            "python3 openrc eudev iproute2 util-linux libqmi qmi-utils "
            "networkmanager bluez wpa_supplicant openssh-server-pam "
            "alsa-ucm-conf alsa-utils sleep-inhibitor dnsmasq "
            "neard-openrc postmarketos-usb-moded usb-signaller>=0.4.3-r4 "
            "unudhcpd>=0.5.0-r2"),
    },
    {
        "post-install": platform_source / "samurai-platform.post-install",
        "post-upgrade": platform_source / "samurai-platform.post-install",
    })

pulse = args.build_root / "samurai-platform-pulse"
copy_file(platform_source / "etc_pulse_daemon.conf.d_90-samurai.conf",
          pulse / "etc/pulse/daemon.conf.d/90-samurai.conf", 0o644)
make_package(
    "samurai-platform-pulse", "5-r15", "noarch", pulse,
    {
        "description": "PulseAudio defaults for Realme X2 Pro",
        "license": "LicenseRef-Local-Project",
        "origin": "samurai-platform",
        "url": "https://github.com/hmhmdcy/edk2-realme-x2-pro",
        "depends": "pulseaudio pulseaudio-bluez",
    })

desktop = args.build_root / "samurai-desktop"
desktop_source = PACKAGES / "samurai-desktop"
copy_file(desktop_source / "samurai-tinydm-stop",
          desktop / "usr/libexec/samurai-tinydm-stop", 0o755)
make_package(
    "samurai-desktop", "4-r16", "noarch", desktop,
    {
        "description": "Realme X2 Pro Plasma Mobile defaults",
        "license": "LicenseRef-Local-Project",
        "origin": "samurai-desktop",
        "url": "https://github.com/hmhmdcy/edk2-realme-x2-pro",
        "depends": (
            "postmarketos-ui-plasma-mobile tinydm samurai-platform "
            "modemmanager bluez samurai-platform-pulse calls chatty "
            "mmsd-tng callaudiod xdg-desktop-portal-kde elogind"),
    },
    {
        "post-install": desktop_source / "samurai-desktop.post-install",
        "post-upgrade": desktop_source / "samurai-desktop.post-install",
    })

index = args.output / "packages.adb"
assert not index.exists()
run([
    args.apk, "--keys-dir", args.trusted_keys, "mkndx",
    "--compression", "deflate:9",
    "--sign-key", args.sign_key,
    "--pkgname-spec", "${name}-${version}.apk",
    "--description", "Realme X2 Pro board packages",
    "--output", index,
    *[str(path) for path in sorted(args.output.glob("*.apk"))],
], "mkndx")
run([args.apk, "--keys-dir", args.trusted_keys, "verify", index],
    "index-verify")

(args.output / "package-manifest.json").write_text(json.dumps({
    "schema": "samurai-board-packages-v1",
    "source_date_epoch": SOURCE_DATE_EPOCH,
    "index_sha256": sha256(index),
    "packages": records,
}, indent=2, sort_keys=True) + "\n")
print(json.dumps({
    "packages": len(records),
    "signed": True,
    "index": str(index),
    "index_sha256": sha256(index),
}))
