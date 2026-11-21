#!/usr/bin/env python3
"""Verify the #516 r6 FAT carrier with the EUD-off integrated DTB."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path("/mnt/e/edk2-samurai-out/charging-management-20261023")
BASE = ROOT / "charging-integration-20261026-fat-private-06"
BASE_FAT = BASE / "logdump-tcpm-sink507-r2-private.img"
OUT = ROOT / "charging-integration-20261026-fat-private-08"
CANDIDATE = OUT / "logdump-eud-off-private-08.img"
CANONICAL_DTB = OUT / "samurai.dtb"
DTB = (
    ROOT
    / "charging-integration-20261026-dtb-private-02"
    / "samurai-eud-off-route-okay.dtb"
)
PARSER = Path(
    "/mnt/e/RealmeX2Pro edk2/reference/charging-oem-audit-20261023/"
    "tcpm-sink-shutdown-candidate/package-logdump.py"
)

BASE_SHA = "975742aef4f0372b616377c6bbfa7f234e2a87218c75f2bf91221facb8ee9c8b"
CANDIDATE_SHA = "dc9e01393c1f3e98babc4020c810b72f63107bebeb0ff31c77683e227011d416"
DTB_SHA = "d7d8a7da7a3fc68b37faceda0fd7c7f506fbbd17b7a510c15cb978b9160acf1b"
IMAGE_SHA = "812f1633e5f92c6ff5e99440a27e03f57d790db6728aee50930719ca5531eddd"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            result.update(chunk)
    return result.hexdigest()


def read_bytes(path: Path) -> bytes:
    with path.open("rb") as source:
        return source.read()


def changed_ranges(left: bytes, right: bytes) -> list[tuple[int, int]]:
    if len(left) != len(right):
        raise RuntimeError("carrier sizes differ")
    ranges: list[tuple[int, int]] = []
    offset = 0
    while offset < len(left):
        if left[offset] == right[offset]:
            offset += 1
            continue
        start = offset
        while offset < len(left) and left[offset] != right[offset]:
            offset += 1
        ranges.append((start, offset))
    return ranges


def merge_ranges(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for low, high in sorted(ranges):
        if merged and low <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(high, merged[-1][1]))
        else:
            merged.append((low, high))
    return merged


def outside_ranges(
    changed: list[tuple[int, int]], allowed: list[tuple[int, int]]
) -> list[tuple[int, int]]:
    outside: list[tuple[int, int]] = []
    for low, high in changed:
        cursor = low
        for allowed_low, allowed_high in allowed:
            if allowed_high <= cursor:
                continue
            if allowed_low >= high:
                break
            if allowed_low > cursor:
                outside.append((cursor, min(high, allowed_low)))
            cursor = max(cursor, allowed_high)
            if cursor >= high:
                break
        if cursor < high:
            outside.append((cursor, high))
    return outside


def allowed_ranges(fs: dict, file_name: str) -> list[tuple[int, int]]:
    entry = fs["files"][file_name]
    ranges = [(offset, offset + 32) for offset in entry["entry_offsets"]]
    for cluster in entry["clusters"]:
        start = fs["data_at"] + (cluster - 2) * fs["bps"]
        ranges.append((start, start + fs["bps"]))
        for copy in range(2):
            fat_offset = fs["fat_at"] + copy * fs["fat_size"] + cluster * 2
            ranges.append((fat_offset, fat_offset + 2))
    return merge_ranges(ranges)


def load_parser():
    spec = importlib.util.spec_from_file_location("fat_parser_r6", PARSER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fdt_value(node: str, prop: str) -> str:
    result = subprocess.run(
        ["/usr/bin/fdtget", "-t", "s", str(CANONICAL_DTB), node, prop],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()


def main() -> None:
    if not OUT.is_dir():
        raise SystemExit(f"missing candidate directory: {OUT}")
    if file_digest(BASE_FAT) != BASE_SHA:
        raise SystemExit("base FAT hash mismatch")
    if file_digest(CANDIDATE) != CANDIDATE_SHA:
        raise SystemExit("candidate FAT hash mismatch")
    if file_digest(DTB) != DTB_SHA:
        raise SystemExit("DTB hash mismatch")

    if CANONICAL_DTB.exists():
        if file_digest(CANONICAL_DTB) != DTB_SHA:
            raise SystemExit("canonical DTB exists with the wrong hash")
    else:
        shutil.copy2(DTB, CANONICAL_DTB)
        with CANONICAL_DTB.open("rb") as stream:
            os.fsync(stream.fileno())

    parser = load_parser()
    old_bytes = read_bytes(BASE_FAT)
    new_bytes = read_bytes(CANDIDATE)
    old = parser.parse_fat(old_bytes)
    new = parser.parse_fat(new_bytes)
    if set(old["files"]) != {"Image", "SAMURAI.DTB"}:
        raise SystemExit("unexpected base FAT files")
    if set(new["files"]) != {"Image", "SAMURAI.DTB"}:
        raise SystemExit("unexpected candidate FAT files")
    if new["files"]["Image"]["content"] != old["files"]["Image"]["content"]:
        raise SystemExit("Image changed unexpectedly")
    if new["files"]["Image"]["sha256"] != IMAGE_SHA:
        raise SystemExit("Image hash mismatch")
    if new["files"]["SAMURAI.DTB"]["content"] != DTB.read_bytes():
        raise SystemExit("candidate DTB content mismatch")
    if new["files"]["SAMURAI.DTB"]["sha256"] != DTB_SHA:
        raise SystemExit("candidate DTB hash mismatch")

    allowed = merge_ranges(
        allowed_ranges(old, "SAMURAI.DTB") + allowed_ranges(new, "SAMURAI.DTB")
    )
    changed = changed_ranges(old_bytes, new_bytes)
    outside = outside_ranges(changed, allowed)
    if outside:
        raise SystemExit(f"non-DTB FAT bytes changed: {outside[:8]}")

    fsck = subprocess.run(
        ["/usr/sbin/fsck.fat", "-n", str(CANDIDATE)],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if fsck.returncode:
        raise SystemExit(f"fsck failed: {fsck.stderr or fsck.stdout}")

    eud_status = fdt_value("/soc@0/serial@88e0000", "status")
    route_status = fdt_value("/soc@0/eud-off-route", "status")
    if eud_status != "disabled":
        raise SystemExit(f"EUD is not disabled: {eud_status}")
    if route_status != "okay":
        raise SystemExit(f"EUD route is not enabled: {route_status}")

    result = {
        "schema": "samurai-fat-private-08-result-v1",
        "passed": True,
        "scope": "offline EUD-off DTB replacement in the #516 Image carrier; no device access",
        "source_fat": {
            "path": str(BASE_FAT),
            "sha256": BASE_SHA,
            "bytes": len(old_bytes),
        },
        "candidate_fat": {
            "path": str(CANDIDATE),
            "sha256": CANDIDATE_SHA,
            "bytes": len(new_bytes),
            "fsck": {
                "returncode": fsck.returncode,
                "stdout": fsck.stdout,
                "stderr": fsck.stderr,
            },
        },
        "source_dtb": {
            "path": str(BASE / "base-DTB-readback"),
            "sha256": old["files"]["SAMURAI.DTB"]["sha256"],
            "bytes": old["files"]["SAMURAI.DTB"]["size"],
        },
        "candidate_dtb": {
            "path": str(CANONICAL_DTB),
            "sha256": DTB_SHA,
            "bytes": CANONICAL_DTB.stat().st_size,
            "eud_status": eud_status,
            "eud_off_route_status": route_status,
        },
        "unchanged_image": {
            "sha256": IMAGE_SHA,
            "bytes": new["files"]["Image"]["size"],
        },
        "fat_integrity": {
            "only_dtb_file_changed": True,
            "Image_file_exact": True,
            "permitted_ranges": allowed,
            "changed_run_count": len(changed),
            "unexpected_changed_ranges": outside,
        },
        "host_space": {
            "C": round(os.statvfs("/mnt/c").f_bavail * os.statvfs("/mnt/c").f_frsize / 1024**3, 2),
            "E": round(os.statvfs("/mnt/e").f_bavail * os.statvfs("/mnt/e").f_frsize / 1024**3, 2),
            "WSL": round(os.statvfs("/").f_bavail * os.statvfs("/").f_frsize / 1024**3, 2),
        },
    }
    (OUT / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    sums = []
    for path in sorted(p for p in OUT.iterdir() if p.is_file() and p.name != "SHA256SUMS"):
        sums.append(f"{file_digest(path)}  {path.name}")
    (OUT / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")
    print(json.dumps({"passed": True, "result": str(OUT / "result.json")}, indent=2))


if __name__ == "__main__":
    main()
