#!/usr/bin/env python3
"""Add the switch_root marker to finalize-plasma.py.

The Plasma finalizer never wrote /etc/samurai-rootfs-release, so the
initramfs refused to switch root and the device stayed in its diagnostic
ramdisk.  finalize-rootfs.py already did this; keep the two paths aligned.

Usage: patch-finalize-plasma.py [PATH]
"""

from pathlib import Path
import sys

MARKER = """
# The embedded initramfs (/usr/sbin/samurai-rootfs) only switch_roots when
# this marker and /sbin/init exist.  finalize-rootfs.py writes it; this
# Plasma path must too, otherwise every boot stays in the diagnostic ramdisk.
release = root / "etc/samurai-rootfs-release"
release.write_text("ROOTFS_ID=samurai-f2fs-rootfs01\\n"
                   "BUILD_PROFILE=github-pmaports-samurai-userspace\\n")
os.chmod(release, 0o644)

"""

ANCHOR = (
    'toml = root / "etc/usb-signaller.d/90-samurai.toml"\n'
    "assert 'default_mode = \"developer_mode\"' in toml.read_text()\n"
)


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "finalize-plasma.py")
    text = path.read_text()
    if "samurai-rootfs-release" in text:
        print(f"{path}: already patched")
        return 0
    if ANCHOR not in text:
        print(f"{path}: anchor not found", file=sys.stderr)
        return 1
    path.write_text(text.replace(ANCHOR, ANCHOR + MARKER, 1))
    print(f"{path}: patched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
