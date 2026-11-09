#!/usr/bin/env python3
"""Audit a samurai DTB for hardcoded RAM or storage-capacity fields."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

import libfdt


def walk(fdt, offset, path, nodes):
    props = {}
    prop_offset = fdt.first_property_offset(
        offset, quiet=libfdt.QUIET_NOTFOUND)
    while prop_offset >= 0:
        prop = fdt.get_property_by_offset(prop_offset)
        props[prop.name] = bytes(prop)
        prop_offset = fdt.next_property_offset(
            prop_offset, quiet=libfdt.QUIET_NOTFOUND)
    nodes[path] = props
    child = fdt.first_subnode(offset, quiet=libfdt.QUIET_NOTFOUND)
    while child >= 0:
        name = fdt.get_name(child)
        walk(fdt, child, path.rstrip("/") + "/" + name, nodes)
        child = fdt.next_subnode(child, quiet=libfdt.QUIET_NOTFOUND)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("dtb", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    data = args.dtb.read_bytes()
    fdt = libfdt.Fdt(data)
    nodes = {}
    walk(fdt, 0, "/", nodes)

    memory_nodes = {
        path: props for path, props in nodes.items()
        if props.get("device_type", b"").rstrip(b"\0") == b"memory"
    }
    memory_details = []
    hardcoded_ram_size = 0
    for path, props in memory_nodes.items():
        reg = props.get("reg", b"")
        cells = list(struct.unpack(f">{len(reg) // 4}I", reg)) \
            if reg and len(reg) % 4 == 0 else []
        size_cells = cells[2:4] if len(cells) == 4 else []
        size = (size_cells[0] << 32) | size_cells[1] if len(
            size_cells) == 2 else None
        if size is not None:
            hardcoded_ram_size += size
        memory_details.append({
            "path": path,
            "reg_hex": reg.hex(),
            "reg_cells": cells,
            "size_bytes": size,
            "is_zero_size_placeholder": size == 0,
        })

    storage_hits = []
    for path, props in nodes.items():
        for name, value in props.items():
            lowered = name.lower()
            if any(token in lowered for token in (
                "userdata", "storage-size", "storage_capacity",
                "capacity-bytes", "emmc-size", "ufs-size",
            )):
                storage_hits.append({"path": path, "property": name})
            text = value.decode("utf-8", "ignore").lower()
            if "userdata" in text or "storage-size" in text:
                storage_hits.append({"path": path, "property": name})

    root = nodes.get("/", {})
    compatible = root.get("compatible", b"").decode(
        "utf-8", "replace").split("\0")
    report = {
        "schema": "samurai-dtb-sku-audit-v1",
        "dtb": str(args.dtb),
        "dtb_sha256": hashlib.sha256(data).hexdigest(),
        "node_count": len(nodes),
        "root_compatible": [item for item in compatible if item],
        "memory_nodes": memory_details,
        "hardcoded_ram_size_bytes": hardcoded_ram_size,
        "storage_capacity_property_hits": storage_hits,
        "passed": (
            bool(memory_details)
            and hardcoded_ram_size == 0
            and not storage_hits
            and "realme,samurai" in compatible
        ),
        "scope": (
            "static DTB audit only; does not prove 6/8/12 GiB or "
            "64/128/256 GB runtime SKU startup"
        ),
    }
    output = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
