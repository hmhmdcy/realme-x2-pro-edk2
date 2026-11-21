#!/usr/bin/env python3
"""Archive metadata for and remove old root-level RX/EUD boot artifacts."""
import hashlib
import json
import re
import time
from pathlib import Path

ROOT = Path(r"E:\edk2-samurai-out")
RECEIPT = Path(__file__).with_name("CLEANUP-ROOT-ARTIFACTS-20261028.json")
PATTERN = re.compile(
    r"^(?:logdump.*\.img|Image-.*|boot-.*\.img|"
    r"SM8150_UEFI-.*\.fd|avbtest_boot\.img|custom_ramdisk\.img)$")
PROTECTED = {
    "boot-samurai-canonical-stockhdr.img",
    "SM8150_UEFI-samurai.fd",
}


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    root = ROOT.resolve(strict=True)
    selected = sorted(
        path for path in root.iterdir()
        if path.is_file() and path.name not in PROTECTED
        and PATTERN.fullmatch(path.name) and path.stat().st_size > 1024 * 1024)
    receipt = {
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "root": str(root),
        "policy": "root-level old RX/EUD artifacts only; protected boot images retained",
        "protected": sorted(PROTECTED),
        "removed": [],
    }
    total = 0
    for path in selected:
        resolved = path.resolve(strict=True)
        if resolved.parent != root:
            raise RuntimeError(f"outside root: {resolved}")
        record = {
            "path": str(resolved),
            "bytes": resolved.stat().st_size,
            "sha256": sha256(resolved),
        }
        resolved.unlink()
        receipt["removed"].append(record)
        total += record["bytes"]
        print(f"removed {resolved.name}")
    receipt["removed_count"] = len(receipt["removed"])
    receipt["removed_bytes"] = total
    tmp = RECEIPT.with_suffix(".json.next")
    tmp.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    tmp.replace(RECEIPT)
    print(f"removed_count={receipt['removed_count']} removed_gib={total / 1024**3:.2f}")


if __name__ == "__main__":
    main()
