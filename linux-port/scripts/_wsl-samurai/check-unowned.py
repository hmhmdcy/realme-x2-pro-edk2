#!/usr/bin/env python3
"""List files in the image that no apk package owns.

An image assembled outside apk ends up with files written straight into the
rootfs.  Those are invisible to `apk upgrade`, cannot be replaced by the
package that logically owns them, and are exactly the "private changes" a
clean distribution build must not contain.

Only /etc and /usr are scanned: /var, /home, /run and /tmp legitimately hold
runtime state, and enablement symlinks under /etc/systemd are generated.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ALLOW = {
    "/etc/apk/world",
    "/etc/apk/arch",
    "/etc/apk/repositories",
    "/etc/machine-id",
    "/etc/ssh/ssh_host_rsa_key",
    "/etc/ssh/ssh_host_rsa_key.pub",
    "/etc/ssh/ssh_host_ecdsa_key",
    "/etc/ssh/ssh_host_ecdsa_key.pub",
    "/etc/ssh/ssh_host_ed25519_key",
    "/etc/ssh/ssh_host_ed25519_key.pub",
}

ALLOW_PREFIX = (
    "/etc/apk/keys/",
    "/etc/apk/repositories.d/",
    "/etc/systemd/system/",
)


def read_owned(db: Path) -> set[str]:
    owned: set[str] = set()
    directory = ""
    for line in db.read_text(errors="replace").splitlines():
        if not line:
            directory = ""
            continue
        code, value = line[0], line[2:]
        if code == "F":
            # The DB stores the path apk installed, e.g. "F:bin" for
            # /usr/bin/coreutils on modern Alpine where /bin -> usr/bin.
            # Accept every prefix, not just etc//usr.
            directory = "/" + value
        elif code == "R" and directory:
            owned.add(directory.rstrip("/") + "/" + value)
    return owned


def owned_paths(root: Path) -> set[str]:
    """Owned paths as a tree walk sees them (resolving /bin -> /usr/bin)."""
    owned = read_owned(root / "lib/apk/db/installed")
    links = {}
    for name in ("bin", "sbin", "lib", "lib64"):
        lp = root / name
        if lp.is_symlink():
            target = str(lp.readlink())
            if target.startswith("usr/"):
                links["/" + name] = "/" + target
    if links:
        extra = set()
        for path in owned:
            for src, dst in links.items():
                if path.startswith(src + "/"):
                    extra.add(dst + path[len(src):])
        owned |= extra
    return owned


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--show", type=int, default=40)
    args = p.parse_args()

    root = args.root
    db = root / "lib/apk/db/installed"
    if not db.is_file():
        print("no apk installed DB", file=sys.stderr)
        return 2
    owned = owned_paths(root)

    unowned = []
    for top in ("etc", "usr"):
        base = root / top
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.is_symlink():
                continue
            rel = "/" + str(path.relative_to(root))
            if rel in owned:
                continue
            if rel in ALLOW or rel.startswith(ALLOW_PREFIX):
                continue
            unowned.append((rel, path.stat().st_size))

    print(f"owned:   {len(owned)} paths")
    print(f"unowned: {len(unowned)} files under /etc and /usr")
    for rel, size in sorted(unowned)[: args.show]:
        print(f"  {size:>8}  {rel}")
    if len(unowned) > args.show:
        print(f"  ... {len(unowned) - args.show} more")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
