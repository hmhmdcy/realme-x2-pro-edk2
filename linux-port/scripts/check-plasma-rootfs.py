#!/usr/bin/env python3
"""Offline verification of the built Plasma Mobile / NCM root tree."""
from pathlib import Path
import argparse, base64, hashlib, json, os, struct, subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--root", type=Path, required=True)
p.add_argument("--packages", type=Path, required=True)
p.add_argument("--user", default="user")
a = p.parse_args()
root, packages = a.root.resolve(), a.packages.resolve()
assert (root / "etc/alpine-release").is_file()

db = (root / "lib/apk/db/installed").read_text()
records = {}
for block in db.split("\n\n"):
    row = {}
    for line in block.splitlines():
        k, _, v = line.partition(":")
        if k in ("P", "V"):
            row[k] = v
    if "P" in row:
        records[row["P"]] = row

required = ["device-realme-samurai", "device-realme-samurai-kernel-none",
            "samurai-camera-config", "samurai-camera-stack", "samurai-desktop",
            "samurai-platform", "samurai-gnss-assist", "samurai-ssc",
            "libcamera", "libcamera-ipa", "libcamera-tools", "libcamera-gstreamer", "libcamera-v4l2",
            "mesa-vulkan-freedreno-samurai", "modemmanager", "libmm-glib", "geoclue",
            "pipewire", "pipewire-libs", "pipewire-spa-libcamera", "gst-plugin-pipewire",
            "samurai-libssc", "samurai-hexagonrpcd",
            "usb-signaller", "unudhcpd", "postmarketos-ui-plasma-mobile",
            "postmarketos-ui-plasma-mobile-extras", "plasma-mobile", "kwin", "openssh-server-pam"]
missing = [n for n in required if n not in records]
assert not missing, missing

selected = set(required)
checks = elfs = 0
for block in db.split("\n\n"):
    current = directory = path = ""
    for line in block.splitlines():
        k, _, value = line.partition(":")
        if k == "P":
            current = value
        elif k == "F":
            directory = value
        elif k == "R":
            path = directory + "/" + value
        elif k == "Z" and current in selected and path:
            f = root / path
            assert f.exists() or f.is_symlink(), "Missing installed file: " + path
            if not f.is_file() or f.is_symlink():
                continue
            if value.startswith(("Q1", "Q2")):
                alg = "sha1" if value[:2] == "Q1" else "sha256"
                if hashlib.new(alg, f.read_bytes()).digest() != base64.b64decode(value[2:]):
                    # Hand-edited config files are listed separately.
                    assert path.startswith(("etc/conf.d/", "etc/ssh/", "home/")), "Package file changed: " + path
                    continue
                checks += 1
                data = f.read_bytes()
                if data.startswith(bytes([127]) + b"ELF"):
                    assert data[4:6] == bytes([2, 1]) and struct.unpack("<H", data[18:20])[0] == 183, "Non-ARM64 ELF: " + path
                    elfs += 1
assert checks > 50, "checksum verification did not run"

# Boot-critical services must exist and be enabled.
services = ["dbus", "elogind", "tinydm", "networkmanager", "sshd", "usb-signaller",
            "modemmanager", "bluetooth", "wpa_supplicant", "unudhcpd.usb0"]
for svc in services:
    path = root / "etc/init.d" / svc
    assert path.exists() or path.is_symlink(), "missing init script " + svc
    assert any((root / "etc/runlevels" / lvl / svc).is_symlink() for lvl in ("boot", "default")), "not enabled " + svc

# NCM path: developer mode, DHCP addresses, sshd policy, user key.
toml = (root / "etc/usb-signaller.d/90-samurai.toml").read_text()
assert 'default_mode = "developer_mode"' in toml
assert "0x0525" in toml and "0xa4a1" in toml
unud = (root / "etc/unudhcpd.conf").read_text()
assert 'UNUDHCPD_SERVER="172.16.42.1"' in unud and 'UNUDHCPD_CLIENT="172.16.42.2"' in unud

entries = [l.split(":") for l in (root / "etc/passwd").read_text().splitlines()]
home = root / next(e[5].lstrip("/") for e in entries if e[0] == a.user)
ak = home / ".ssh/authorized_keys"
assert ak.is_file() and ak.read_text().strip().startswith("ssh-"), "missing SSH key"
# No board-private sshd drop-in: 50-postmarketos-ui-policy.conf sets
# UsePAM yes and openssh defaults already allow password auth.  `sshd -T` in
# a chroot of this image was identical with and without 99-samurai.conf.
assert not (root / "etc/ssh/sshd_config.d/99-samurai.conf").exists(), \
    "unowned 99-samurai.conf is back; it duplicates openssh defaults"

# pam_unix's unprivileged helper is setgid shadow.  Keep /etc/shadow
# readable by that group so the Plasma lock screen can authenticate without
# relying on the root-only sudo path.
shadow_group = next(
    int(line.split(":")[2])
    for line in (root / "etc/group").read_text().splitlines()
    if line.startswith("shadow:")
)
shadow_stat = (root / "etc/shadow").stat()
assert shadow_stat.st_uid == 0 and shadow_stat.st_gid == shadow_group, \
    "etc/shadow must be root:shadow"
assert shadow_stat.st_mode & 0o777 == 0o640, "etc/shadow must be mode 0640"

tinydm = (root / "etc/conf.d/tinydm").read_text()
assert 'AUTOLOGIN_UID="10000"' in tinydm, "tinydm autologin UID not set"
session = root / "usr/share/wayland-sessions/plasma-mobile.desktop"
assert session.is_file(), "Plasma Mobile session entry missing"
default_session = root / "var/lib/tinydm/default-session.desktop"
assert default_session.is_symlink(), "tinydm default session missing"
assert os.readlink(default_session) == "/" + session.relative_to(root).as_posix(), \
    "tinydm points at the wrong session"
assert "AUTOLOGIN_CMD" not in tinydm, "unsupported AUTOLOGIN_CMD left behind"

fw = root / "lib/firmware/qcom/sm8150/realme/samurai"
assert fw.is_dir() and any(fw.iterdir()), "firmware not provisioned"
assert (root / "var/lib/samurai/firmware").is_dir()

gi = subprocess.run(["chroot", str(root), "/usr/bin/python3", "-c",
                     "import gi; gi.require_version('Qmi','1.0'); from gi.repository import Qmi; print('GI-QMI-load-ok')"],
                    capture_output=True, text=True)
assert gi.returncode == 0, gi.stderr

print(json.dumps({
    "installed_package_count": len(records),
    "custom_packages": {n: records[n]["V"] for n in required if n in records},
    "installed_files_verified": checks,
    "arm64_elfs_verified": elfs,
    "services_enabled": services,
    "ncm_developer_mode": True,
    "ssh_public_key": True,
    "ui_autologin": "plasma-mobile",
    "gi_qmi_namespace_loaded": True,
    "hardware_tested": False,
}, indent=2))
