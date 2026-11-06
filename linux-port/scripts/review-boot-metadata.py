#!/usr/bin/env python3
"""Review non-DTB module changes in a samurai boot-image candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import lzma
import re
import struct
import sys
import uuid
import zlib
from pathlib import Path


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_helpers(repo_root: Path) -> dict:
    source = (
        repo_root / "reference/kernel104/verify-firmware.py"
    ).read_text(encoding="utf-8").split("dt_audit=")[0]
    namespace = {}
    exec(compile(source, "verify-firmware-helpers", "exec"), namespace)
    return namespace


def align(value: int, alignment: int) -> int:
    return (value + alignment - 1) // alignment * alignment


def unpack_boot(boot: bytes, compat: bytes, helpers: dict) -> dict:
    assert boot[:8] == b"ANDROID!"
    kernel_size, ramdisk_size, second_size, page, version = [
        struct.unpack_from("<I", boot, offset)[0]
        for offset in (8, 16, 24, 36, 40)
    ]
    assert page == 2048 and version == 1
    assert ramdisk_size == 1 and second_size == 0
    size = page + align(kernel_size, page) + align(ramdisk_size, page)
    decompressor = zlib.decompressobj(31)
    raw = (
        decompressor.decompress(boot[page:page + kernel_size])
        + decompressor.flush()
    )
    assert decompressor.eof and not decompressor.unconsumed_tail
    assert decompressor.unused_data == compat
    shim = raw[:144]
    fd = raw[144:]
    assert len(fd) == 0x700000
    compact = helpers["fv"](fd)
    images = [item for item in compact.values() if item["type"] == 0xB]
    assert len(images) == 1 and len(images[0]["sections"]) == 1
    section_type, body, section = images[0]["sections"][0]
    assert section_type == 2
    assert str(uuid.UUID(bytes_le=body[:16])) == helpers["lz_guid"]
    offset, _attrs = struct.unpack_from("<HH", body, 16)
    nested = helpers["sections"](
        lzma.decompress(section[offset:], format=lzma.FORMAT_ALONE)
    )
    assert len(nested) == 1 and nested[0][0] == 0x17
    return {
        "shim": shim,
        "fd": fd,
        "main": nested[0][1],
        "modules": helpers["fv"](nested[0][1]),
    }


def changed_ranges(before: bytes, after: bytes) -> list[dict]:
    common = min(len(before), len(after))
    ranges = []
    start = None
    for index, (left, right) in enumerate(zip(before[:common], after[:common])):
        if left != right and start is None:
            start = index
        elif left == right and start is not None:
            ranges.append({
                "offset": start,
                "length": index - start,
                "before": before[start:index],
                "after": after[start:index],
            })
            start = None
    if start is not None:
        ranges.append({
            "offset": start,
            "length": common - start,
            "before": before[start:],
            "after": after[start:],
        })
    if len(before) != len(after):
        ranges.append({
            "offset": common,
            "length": abs(len(before) - len(after)),
            "before": before[common:],
            "after": after[common:],
        })
    return ranges


def printable(value: bytes) -> bool:
    if not value:
        return True
    if len(value) % 2 == 0:
        try:
            text = value.decode("utf-16-le")
            if text and all(ch.isprintable() or ch in "\r\n\t" for ch in text):
                return True
        except UnicodeDecodeError:
            pass
    try:
        text = value.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return bool(text) and all(ch.isprintable() or ch in "\r\n\t" for ch in text)


def decode_range(value: bytes) -> dict:
    result = {"hex": value.hex()}
    if len(value) % 2 == 0:
        try:
            text = value.decode("utf-16-le")
            if all(ch.isprintable() or ch in "\r\n\t" for ch in text):
                result["utf16le"] = text
        except UnicodeDecodeError:
            pass
    try:
        text = value.decode("utf-8")
        if all(ch.isprintable() or ch in "\r\n\t" for ch in text):
            result["utf8"] = text
    except UnicodeDecodeError:
        pass
    return result


def review_module(before: bytes, after: bytes) -> dict:
    ranges = changed_ranges(before, after)
    same_length = len(before) == len(after)
    printable_only = same_length and bool(ranges) and all(
        printable(item["before"]) and printable(item["after"])
        for item in ranges
    )
    if not ranges and same_length:
        classification = "identical"
    elif not same_length:
        classification = "length_changed_review"
    elif printable_only:
        classification = "printable_metadata_only"
    else:
        classification = "binary_change_review"
    return {
        "before_bytes": len(before),
        "after_bytes": len(after),
        "before_sha256": sha256(before),
        "after_sha256": sha256(after),
        "same_length": same_length,
        "byte_length_delta": len(after) - len(before),
        "changed_byte_count": sum(item["length"] for item in ranges),
        "changed_ranges": [
            {
                "offset": item["offset"],
                "length": item["length"],
                "before": decode_range(item["before"]),
                "after": decode_range(item["after"]),
            }
            for item in ranges[:32]
        ],
        "changed_range_count": len(ranges),
        "all_changed_ranges_printable": printable_only,
        "classification": classification,
    }


def module_names(modules: dict) -> dict[str, dict]:
    result = {}
    for guid, module in modules.items():
        name = module.get("name") or guid
        result[name] = {"guid": guid, **module}
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--workspace-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
    )
    parser.add_argument("--source-boot", required=True, type=Path)
    parser.add_argument("--candidate-boot", required=True, type=Path)
    parser.add_argument("--compat-dtb", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    helpers = load_helpers(args.workspace_root)
    compat = args.compat_dtb.read_bytes()
    source = unpack_boot(args.source_boot.read_bytes(), compat, helpers)
    candidate = unpack_boot(args.candidate_boot.read_bytes(), compat, helpers)
    before_modules = module_names(source["modules"])
    after_modules = module_names(candidate["modules"])

    if set(before_modules) != set(after_modules):
        raise SystemExit("module name set differs between source and candidate")

    metadata_names = {
        "PlatformSmbiosDxe",
        "BdsDxe",
        "UiApp",
    }
    reviewed = {}
    for name in sorted(metadata_names):
        if name not in before_modules or name not in after_modules:
            raise SystemExit(f"missing module: {name}")
        reviewed[name] = review_module(
            before_modules[name]["body"],
            after_modules[name]["body"],
        )

    all_printable = all(
        item["classification"] in ("identical", "printable_metadata_only")
        for item in reviewed.values()
    )
    report = {
        "schema": "samurai-boot-metadata-review-v1",
        "passed": all_printable,
        "source_boot": str(args.source_boot),
        "source_boot_sha256": sha256(args.source_boot.read_bytes()),
        "candidate_boot": str(args.candidate_boot),
        "candidate_boot_sha256": sha256(args.candidate_boot.read_bytes()),
        "metadata_modules": reviewed,
        "classification": (
            "printable_metadata_only"
            if all_printable else "requires_manual_review"
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if all_printable else 2


if __name__ == "__main__":
    raise SystemExit(main())
