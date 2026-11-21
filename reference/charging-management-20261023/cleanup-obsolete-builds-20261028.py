#!/usr/bin/env python3
"""Remove only the obsolete E: build volumes listed in the cleanup receipt."""
import os
import shutil
from pathlib import Path

ROOT = Path(r"E:\edk2-samurai-out").resolve()
FILES = [
    ROOT / "kernel282/full-kernel-build282.ext4",
    ROOT / "cleanup20261019/kernel118-current-build-volume.ext4.zst",
    ROOT / "rx61/EWDK_ge_release_svc_prod1_26100_250904-1728.iso",
]
DIRECTORIES = [
    ROOT / "cleanup145/volumes",
]


def confirm(path):
    resolved = path.resolve(strict=True)
    if ROOT not in resolved.parents:
        raise RuntimeError(f"outside cleanup root: {resolved}")
    return resolved


def main():
    for path in FILES:
        resolved = confirm(path)
        if not resolved.is_file():
            raise RuntimeError(f"not a regular file: {resolved}")
        print(f"remove file {resolved} ({resolved.stat().st_size} bytes)")
        resolved.unlink()
    for path in DIRECTORIES:
        resolved = confirm(path)
        if not resolved.is_dir():
            raise RuntimeError(f"not a directory: {resolved}")
        print(f"remove directory {resolved}")
        shutil.rmtree(resolved)
    print("obsolete build cleanup complete")


if __name__ == "__main__":
    main()
