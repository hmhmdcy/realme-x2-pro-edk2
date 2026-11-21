#!/usr/bin/env python3
"""Configure the built Plasma Mobile root tree for first boot without hardware access."""
from pathlib import Path
import argparse, json, os, uuid, re

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--root", type=Path, required=True)
p.add_argument("--user", default="user")
p.add_argument("--authorized-key", type=Path)
a = p.parse_args()
root = a.root.resolve()
assert (root / "etc/alpine-release").is_file(), "offline Alpine root required"
assert not os.statvfs(root).f_flag & os.ST_RDONLY

identity = root / "etc/machine-id"
if not identity.exists() or not identity.read_text().strip():
    identity.write_text(uuid.uuid4().hex + "\n")

# pmbootstrap install records locally built APKs as "<name><Q1...=", i.e. a
# checksum pin to the exact artifact. That makes the next apk upgrade reject
# newer builds. Keep the intended package names only, so the image tracks the
# release repository like a normal postmarketOS installation.
world = root / "etc/apk/world"
if world.is_file():
    kept = []
    for line in world.read_text().splitlines():
        name = line.strip()
        if not name or name.startswith("#"):
            continue
        name = re.sub(r"[<>=]+Q[12][A-Za-z0-9+/]+=*$", "", name)
        if name not in kept:
            kept.append(name)
    world.write_text("\n".join(kept) + "\n")

# This device is kernel=none: the boot chain mounts the F2FS rootfs directly
# (root=PARTLABEL=userdata rootfstype=f2fs) and there is no initramfs in use.
# The packaged postmarketos-mkinitfs apk trigger still calls `mkinitfs`, which
# aborts with "only one kernel release/flavor is supported, found: []". apk
# then records the package as broken_script (the f:s flag in the installed
# database), and every later transaction -- successful upgrades included --
# ends with "1 error" and a non-zero exit code.
#
# mkinitfs ships KERNEL_INSTALL_BYPASS for exactly this case: setting it to 1
# makes the tool log the skip and exit 0 without touching the boot chain. Gate
# it on the board package's own external-kernel marker so a rebuilt image
# never silently skips initramfs generation on a device that does need one.
def guard_external_kernel_trigger():
    """Make the packaged trigger a no-op when the kernel lives outside apk."""
    import tarfile
    import tempfile

    marker = root / "usr/share/samurai/external-kernel.txt"
    if not marker.is_file():
        return False

    archive_path = root / "lib/apk/db/scripts.tar.gz"
    if not archive_path.is_file():
        return False

    members, infos = {}, []
    with tarfile.open(archive_path) as archive:
        for info in archive.getmembers():
            infos.append(info)
            if info.isfile():
                members[info.name] = archive.extractfile(info).read()

    names = [n for n in members
             if n.startswith("postmarketos-mkinitfs-") and n.endswith(".trigger")]
    assert len(names) == 1, f"expected one mkinitfs trigger, got {names}"
    name = names[0]
    body = members[name].decode()
    if "KERNEL_INSTALL_BYPASS" in body:
        return False
    anchor = "/usr/sbin/mkinitfs"
    assert body.rstrip().endswith(anchor), "unexpected mkinitfs trigger layout"
    members[name] = body.rstrip()[:-len(anchor)].rstrip().encode() + \
        b"\n# kernel=none: no installed kernel release to build an initramfs for.\n" \
        b"KERNEL_INSTALL_BYPASS=1 /usr/sbin/mkinitfs\n"

    fd, tmp = tempfile.mkstemp(dir=str(archive_path.parent))
    os.close(fd)
    with tarfile.open(tmp, "w:gz") as archive:
        for info in infos:
            data = members.get(info.name)
            if data is not None:
                info.size = len(data)
            archive.addfile(info, __import__("io").BytesIO(data) if data is not None else None)
    os.chmod(tmp, 0o600)
    os.replace(tmp, archive_path)
    return True


external_kernel_guarded = guard_external_kernel_trigger()


def clear_stale_broken_mkinitfs():
    """Drop the broken_script flag a failed build-time trigger left behind.

    A rootfs built before the trigger guard existed ran mkinitfs without a
    kernel.release, so apk recorded postmarketos-mkinitfs as broken_script
    ("f:s"). apk then reports "1 error" on every later transaction. Both causes
    are fixed above, so the historical flag is stale and must not ship.
    """
    installed = root / "lib/apk/db/installed"
    if not installed.is_file():
        return False
    blocks = installed.read_text().split("\n\n")
    changed = False
    out = []
    for block in blocks:
        fields = {}
        for line in block.split("\n"):
            if len(line) > 1 and line[1] == ":":
                fields.setdefault(line[0], line[2:])
        if fields.get("P") == "postmarketos-mkinitfs" and fields.get("f") == "s":
            lines = [l for l in block.split("\n") if l != "f:s"]
            block = "\n".join(lines)
            changed = True
        out.append(block)
    if changed:
        installed.write_text("\n\n".join(out))
    return changed


stale_flag_cleared = clear_stale_broken_mkinitfs()

entries = [s.split(":") for s in (root / "etc/passwd").read_text().splitlines()]
u = next(e for e in entries if e[0] == a.user)
uid, gid = map(int, u[2:4])
home = root / u[5].lstrip("/")

systemd = (root / "usr/lib/systemd/system").is_dir()

if systemd:
    # plasma-mobile.service hardcodes User=1000 upstream; this image creates
    # the default account as uid 10000.
    dropin = root / "etc/systemd/system/plasma-mobile.service.d/10-samurai.conf"
    dropin.parent.mkdir(parents=True, exist_ok=True)
    dropin.write_text(
        "# postmarketOS creates the default user as uid/gid 10000 on this image;\n"
        "# the upstream unit hardcodes 1000.\n"
        f"[Service]\nUser={uid}\nGroup={gid}\n")
    dm = root / "etc/systemd/system/display-manager.service"
    if not dm.is_symlink():
        dm.symlink_to("/usr/lib/systemd/system/plasma-mobile.service")
else:
    confd = root / "etc/conf.d/tinydm"
    text = confd.read_text()
    text = re.sub(r"^AUTOLOGIN_UID=.*$", "", text, flags=re.M)
    text = text.rstrip() + f'\nAUTOLOGIN_UID="{uid}"\n'
    confd.write_text(text)

# tinydm resolves the session through this symlink; without it,
# tinydm-run-session exits immediately with "no session configured".
session = root / "usr/share/wayland-sessions/plasma-mobile.desktop"
assert session.is_file(), "Plasma Mobile session entry missing"
target = root / "var/lib/tinydm/default-session.desktop"
if systemd:
    target = None
if target is not None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_symlink() or target.exists():
        target.unlink()
    target.symlink_to("/" + session.relative_to(root).as_posix())

def svc_exists(name):
    p = root / "etc/init.d" / name
    return p.exists() or p.is_symlink()

# elogind in Alpine/pmOS reads /etc/elogind/logind.conf; postmarketos-base-ui
# installs its HandlePowerKey=ignore policy under /usr/lib/elogind/logind.conf.
# Without syncing /etc/elogind/logind.conf, elogind defaults to poweroff.
usr_logind = root / "usr/lib/elogind/logind.conf"
etc_logind = root / "etc/elogind/logind.conf"
if usr_logind.is_file() and not etc_logind.exists():
    etc_logind.parent.mkdir(parents=True, exist_ok=True)
    etc_logind.write_text(usr_logind.read_text())

if systemd:
    # The packed samurai-systemd unit ships this preset and its post-install
    # enables the units.  Only reclone the links that the offline image build
    # cannot create, so a rebuilt tree stays bootable without running
    # systemctl inside the host chroot.
    wants = root / "etc/systemd/system/multi-user.target.wants"
    wants.mkdir(parents=True, exist_ok=True)
    for unit in [
        "samurai-radio.service", "samurai-ssc.service",
        "samurai-gnss-assist.service", "samurai-usb-network.service",
        "samurai-usb-recover.service", "usb-signaller.service",
        "usb-signaller-developer-mode.service", "unudhcpd@usb0.service",
        "NetworkManager.service", "ModemManager.service",
        "iio-sensor-proxy.service", "sshd.service",
    ]:
        src = root / "usr/lib/systemd/system" / unit
        if not src.is_file():
            continue
        link = wants / unit
        if not link.is_symlink():
            link.symlink_to("/usr/lib/systemd/system/" + unit)
else:
    runlevels = root / "etc/runlevels"
    want = {"boot": ["unudhcpd.usb0"],
            "default": ["dbus", "elogind", "tinydm", "networkmanager", "sshd",
                        "usb-signaller", "modemmanager", "bluetooth", "wpa_supplicant"]}
    optional_board_default = [
        "samurai-radio", "samurai-ssc", "iio-sensor-proxy",
        "postmarketos-zram-swap", "neard",
    ]
    for level, names in want.items():
        d = runlevels / level
        d.mkdir(parents=True, exist_ok=True)
        for name in names:
            assert svc_exists(name), name
            link = d / name
            if not link.is_symlink():
                link.symlink_to("/etc/init.d/" + name)

    for name in optional_board_default:
        if svc_exists(name):
            link = runlevels / "default" / name
            if not link.is_symlink():
                link.symlink_to("/etc/init.d/" + name)

# No sshd drop-in is written.  `50-postmarketos-ui-policy.conf` already sets
# UsePAM yes, and openssh's own defaults are PasswordAuthentication yes /
# KbdInteractiveAuthentication yes.  Measured with `sshd -T` inside a chroot
# of this image: removing this file leaves every value identical, so it was
# an unowned duplicate that `apk upgrade` could never manage.
stray_sshd = root / "etc/ssh/sshd_config.d/99-samurai.conf"
if stray_sshd.is_file():
    stray_sshd.unlink()

# urfkilld defaults to key_control=true, which EVIOCGRABs /dev/input/event*.
# On this handset the Wayland compositor already owns the GPIO key device, so
# the grab fails and urfkilld exits 1. Upstream guidance for hardware rfkill
# keys is key_control=false; the live device stays up with it.
urfkill_conf = root / "etc/urfkill/urfkill.conf"
if urfkill_conf.is_file():
    text = urfkill_conf.read_text()
    if "key_control=false" not in text:
        if "# key_control=true" in text:
            text = text.replace("# key_control=true", "key_control=false")
        elif "key_control=true" in text:
            text = text.replace("key_control=true", "key_control=false")
        else:
            text = text.rstrip() + "\nkey_control=false\n"
        urfkill_conf.write_text(text)
hardware_conf = root / "etc/urfkill/hardware.conf"
if hardware_conf.exists():
    hardware_conf.unlink()

if a.authorized_key and a.authorized_key.is_file():
    key = a.authorized_key.read_text().strip()
    assert key.startswith(("ssh-", "ecdsa-", "sk-")), "not an OpenSSH public key"
    ak = home / ".ssh/authorized_keys"
    ak.parent.mkdir(parents=True, exist_ok=True)
    ak.write_text(key + "\n")
    os.chmod(ak, 0o600)
    os.chown(ak, uid, gid)
    os.chmod(ak.parent, 0o700)
    os.chown(ak.parent, uid, gid)

toml = root / "etc/usb-signaller.d/90-samurai.toml"
assert 'default_mode = "developer_mode"' in toml.read_text()

print(json.dumps({"configured": True, "user": a.user, "uid": uid,
                  "autologin": "plasma-mobile",
                  "ssh_key_installed": bool(a.authorized_key and a.authorized_key.is_file()),
                  "ncm_default": "developer_mode"}, indent=2))
