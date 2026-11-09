#!/usr/bin/env python3
"""Compare two DTBs while normalizing phandle renumbering."""

from __future__ import annotations

import argparse
import hashlib
import json
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


def load(path):
    fdt = libfdt.Fdt(path.read_bytes())
    nodes = {}
    walk(fdt, 0, "/", nodes)
    handles = {}
    for node_path, props in nodes.items():
        for name in ("phandle", "linux,phandle"):
            value = props.get(name)
            if value is not None and len(value) == 4:
                handles[int.from_bytes(value, "big")] = node_path
    return nodes, handles


# Properties whose value is a list of phandles with no trailing cells.
PHANDLE_LIST_PROPERTIES = {
    "assigned-clock-parents",
    "flash-leds",
    "memory-region",
    "power-supplies",
}

# Properties whose value is a list of (phandle, argument cells).
SPECIFIER_REFERENCES = {
    "assigned-clocks": ("#clock-cells", 1),
    "clocks": ("#clock-cells", 1),
    "cooling-device": ("#cooling-cells", 2),
    "dmas": ("#dma-cells", 1),
    "hwlocks": ("#hwlock-cells", 1),
    "interconnects": ("#interconnect-cells", 1),
    "interrupts-extended": ("#interrupt-cells", 2),
    "io-channels": ("#io-channel-cells", 1),
    "iommus": ("#iommu-cells", 2),
    "mboxes": ("#mbox-cells", 1),
    "phys": ("#phy-cells", 1),
    "power-domains": ("#power-domain-cells", 0),
    "resets": ("#reset-cells", 1),
    "sound-dai": ("#sound-dai-cells", 0),
    "thermal-sensors": ("#thermal-sensor-cells", 0),
}

SINGLE_REFERENCES = {
    "interrupt-parent",
    "lens-focus",
    "nvmem-cells",
    "operating-points-v2",
    "qcom,address-setup-supplier",
    "qcom,bcm-voters",
    "qcom,camss",
    "qcom,gmu",
    "qcom,qmp",
    "qcom,rproc",
    "realme,eud-hardware",
    "realme,usb-controller",
    "remote-endpoint",
    "remoteproc",
    "required-opps",
    "slim-ifc-dev",
    "trip",
    "wakeup-parent",
}


def cell_count(nodes, path, property_name, default):
    value = nodes.get(path, {}).get(property_name)
    return int.from_bytes(value, "big") if value else default


def specifier_offsets(value, handles, nodes, cells_property, default):
    result = []
    offset = 0
    while offset + 4 <= len(value):
        target = handles.get(int.from_bytes(value[offset:offset + 4], "big"))
        result.append(offset)
        cells = (
            cell_count(nodes, target, cells_property, default)
            if target is not None else default
        )
        offset += 4 * (1 + cells)
    return result


def reference_offsets(name, value, handles, nodes):
    length = len(value)
    if name == "gpio-ranges":
        return range(0, length, 16)
    if name == "iommu-addresses":
        return range(0, length, 20)
    if name == "iommu-map":
        # The upstream binding uses four cells; the SM8150 vendor tree in
        # this project uses five. In both layouts the phandle is the second
        # cell of each entry.
        if length % 20 == 0 and length >= 20:
            return range(4, length, 20)
        return range(4, length, 16)
    if name == "qcom,smem-states":
        return range(0, length, 8)
    if name in PHANDLE_LIST_PROPERTIES:
        return range(0, length, 4)
    if name in SINGLE_REFERENCES or name.endswith("-supply"):
        return (0,)
    if name.endswith("-gpios") or name in {
            "gpio", "gpios", "enable-gpio"}:
        return range(0, length, 12)
    if name.startswith("pinctrl-") and name != "pinctrl-names":
        return range(0, length, 4)
    if name in SPECIFIER_REFERENCES:
        cells_property, default = SPECIFIER_REFERENCES[name]
        return specifier_offsets(
            value, handles, nodes, cells_property, default)
    return ()


def normalize(value, handles, nodes, name):
    if len(value) % 4:
        return value
    refs = set(reference_offsets(name, value, handles, nodes))
    output = bytearray()
    for offset in range(0, len(value), 4):
        cell = int.from_bytes(value[offset:offset + 4], "big")
        target = handles.get(cell) if offset in refs else None
        if target is None:
            output.extend(value[offset:offset + 4])
        else:
            output.extend(b"phandle:" + target.encode() + b"\0")
    return bytes(output)


def display(value):
    if value is None:
        return None
    try:
        text = value.rstrip(b"\0").decode("utf-8")
        if text and all(ch.isprintable() or ch in "\n\t" for ch in text):
            return {"text": text}
    except UnicodeDecodeError:
        pass
    return {"hex": value.hex()}


parser = argparse.ArgumentParser()
parser.add_argument("before", type=Path)
parser.add_argument("after", type=Path)
parser.add_argument("--output", type=Path)
args = parser.parse_args()

before_nodes, before_handles = load(args.before)
after_nodes, after_handles = load(args.after)

only_before = sorted(before_nodes.keys() - after_nodes.keys())
only_after = sorted(after_nodes.keys() - before_nodes.keys())
only_before_props = []
only_after_props = []
only_before_phandle_props = []
only_after_phandle_props = []
phandle_value_only = []
reference_normalized = []
changed = []

for path in sorted(before_nodes.keys() & after_nodes.keys()):
    before = before_nodes[path]
    after = after_nodes[path]
    for name in sorted(before.keys() - after.keys()):
        item = {"path": path, "property": name}
        if name in ("phandle", "linux,phandle"):
            only_before_phandle_props.append(item)
        else:
            only_before_props.append(item)
    for name in sorted(after.keys() - before.keys()):
        item = {"path": path, "property": name}
        if name in ("phandle", "linux,phandle"):
            only_after_phandle_props.append(item)
        else:
            only_after_props.append(item)
    for name in sorted(before.keys() & after.keys()):
        if name in ("phandle", "linux,phandle"):
            if before[name] != after[name]:
                phandle_value_only.append({"path": path, "property": name})
            continue
        if before[name] == after[name]:
            continue
        if normalize(before[name], before_handles, before_nodes, name) == normalize(
                after[name], after_handles, after_nodes, name):
            reference_normalized.append({"path": path, "property": name})
            continue
        changed.append({
            "path": path,
            "property": name,
            "before": display(before[name]),
            "after": display(after[name]),
        })

result = {
    "schema": "samurai-dtb-semantic-diff-v2",
    "before": str(args.before),
    "after": str(args.after),
    "before_sha256": hashlib.sha256(args.before.read_bytes()).hexdigest(),
    "after_sha256": hashlib.sha256(args.after.read_bytes()).hexdigest(),
    "before_nodes": len(before_nodes),
    "after_nodes": len(after_nodes),
    "only_before_nodes": only_before,
    "only_after_nodes": only_after,
    "only_before_properties": only_before_props,
    "only_after_properties": only_after_props,
    "only_before_phandle_properties": only_before_phandle_props,
    "only_after_phandle_properties": only_after_phandle_props,
    "phandle_value_only": phandle_value_only,
    "reference_normalized_properties": reference_normalized,
    "changed_properties": changed,
    "summary": {
        "only_before_node_count": len(only_before),
        "only_after_node_count": len(only_after),
        "only_before_property_count": len(only_before_props),
        "only_after_property_count": len(only_after_props),
        "only_before_phandle_property_count": len(only_before_phandle_props),
        "only_after_phandle_property_count": len(only_after_phandle_props),
        "phandle_value_only_count": len(phandle_value_only),
        "reference_normalized_property_count": len(reference_normalized),
        "changed_property_count": len(changed),
    },
}

text = json.dumps(result, indent=2, sort_keys=True) + "\n"
if args.output:
    args.output.write_text(text, encoding="utf-8")
print(text, end="")
