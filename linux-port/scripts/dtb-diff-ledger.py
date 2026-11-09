#!/usr/bin/env python3
"""Classify a samurai DTB semantic diff into an auditable experiment ledger."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


SCHEMA = "samurai-dtb-semantic-diff-v2"
LEDGER_SCHEMA = "samurai-dtb-difference-ledger-v1"


CATEGORY_ORDER = (
    "camera_icp_experiment",
    "charging_usb_input_experiment",
    "usb_controller_linkage",
    "eud_debug_route",
    "debug_and_test_bootargs",
    "vendor_compat_fields",
)


CATEGORY_META = {
    "camera_icp_experiment": {
        "title": "Camera ICP experiment",
        "disposition": "optional_overlay_not_in_samurai_dt_v1",
        "public_abi": False,
        "reason": (
            "Adds the out-of-tree SM8150 camera ICP node, its firmware name, "
            "and five IOVA reservations. Camera work is paused and this "
            "block has not been accepted as a stable v1 hardware contract."
        ),
        "evidence": [
            "/soc@0/icp@ac10000 uses qcom,sm8150-camss-icp and "
            "firmware-name qcom/sm8150/camera-icp.elf",
            "reservation-icp-* nodes are absent from the canonical k363 DTB",
            "memory@9ab00000 gains a phandle only because the ICP node "
            "references it",
        ],
    },
    "charging_usb_input_experiment": {
        "title": "Charging and USB input experiment",
        "disposition": "optional_overlay_not_in_samurai_dt_v1",
        "public_abi": False,
        "reason": (
            "Adds the Realme USB-input / APSD handoff path, measured VBUS "
            "ADC, Type-C policy connector, and DWC3 power_supply glue. "
            "These are active charging experiments, not a frozen board ABI."
        ),
        "evidence": [
            "samurai-measured-vbus.dtsi adds ADC channel 8 and the "
            "usb-c-connector sink policy",
            "realme,apsd-handoff-trial and usb-psy-name are experiment "
            "integration inputs",
            "typec@1500 changes from disabled to okay in the deployed DTB",
        ],
    },
    "eud_debug_route": {
        "title": "EUD debug route",
        "disposition": "debug_only_exclude_from_production_dtb",
        "public_abi": False,
        "reason": (
            "The eud-off-route node and the serial@88e0000 status change "
            "are debug transport policy. They must not become part of the "
            "production hardware contract."
        ),
        "evidence": [
            "/soc@0/eud-off-route is absent from the canonical k363 DTB",
            "serial@88e0000 changes from okay to disabled in the deployed "
            "experiment",
        ],
    },
    "usb_controller_linkage": {
        "title": "USB controller linkage",
        "disposition": "linkage_only_not_a_hardware_policy",
        "public_abi": False,
        "reason": (
            "The DWC3 node gains a phandle because either the charging "
            "experiment or the EUD route references it. The phandle is a "
            "graph edge, not a stable hardware policy; classify it "
            "separately from the charging contract."
        ),
        "evidence": [
            "the same phandle appears in the isolated EUD debug profile",
            "the charging profile references the DWC3 node through "
            "usb-psy-name as well",
        ],
    },
    "debug_and_test_bootargs": {
        "title": "Debug and test bootargs",
        "disposition": "move_to_debug_startup_entry",
        "public_abi": False,
        "reason": (
            "The deployed bootargs removes the EUD early console and adds "
            "bq27xxx_battery.samurai_instant_current=1. Boot policy belongs "
            "in the boot entry or LoadOptions, not in the hardware ABI."
        ),
        "evidence": [
            "canonical bootargs contains earlycon=eud and console=eud",
            "deployed bootargs removes both and adds the battery test knob",
        ],
    },
    "vendor_compat_fields": {
        "title": "Vendor ABL/DTBO match fields",
        "disposition": "vendor_compat_only_exclude_from_os_dtb",
        "public_abi": False,
        "reason": (
            "These root properties are consumed by the stock ABL/DTBO "
            "compatibility path. They are not Linux board ABI and belong "
            "only in the vendor/compat DTB."
        ),
        "evidence": [
            "qcom,msm-id, qcom,board-id, and oppo,dtsi_no are matched by "
            "the stock boot chain",
            "the source split already removes them from the OS-facing DTB",
        ],
    },
}


EXACT_NODE_CATEGORIES = {
    "/soc@0/icp@ac10000": "camera_icp_experiment",
    "/soc@0/eud-off-route": "eud_debug_route",
    "/soc@0/spmi@c440000/pmic@2/usb-input@1300":
        "charging_usb_input_experiment",
    "/soc@0/spmi@c440000/pmic@2/adc@3100/channel@8":
        "charging_usb_input_experiment",
    "/soc@0/spmi@c440000/pmic@2/typec@1500/connector":
        "charging_usb_input_experiment",
}


EXACT_PROPERTY_CATEGORIES = {
    ("/soc@0/geniqup@8c0000/i2c@884000/charger@5c", "typec-supply"):
        "charging_usb_input_experiment",
    ("/soc@0/spmi@c440000/pmic@2/typec@1500", "io-channel-names"):
        "charging_usb_input_experiment",
    ("/soc@0/spmi@c440000/pmic@2/typec@1500", "io-channels"):
        "charging_usb_input_experiment",
    ("/soc@0/spmi@c440000/pmic@2/typec@1500", "power-supplies"):
        "charging_usb_input_experiment",
    ("/soc@0/spmi@c440000/pmic@2/typec@1500",
     "realme,apsd-handoff-trial"):
        "charging_usb_input_experiment",
    ("/soc@0/spmi@c440000/pmic@2/typec@1500", "vdd-pdphy-supply"):
        "charging_usb_input_experiment",
    ("/soc@0/usb@a6f8800/usb@a600000", "usb-psy-name"):
        "charging_usb_input_experiment",
    ("/chosen", "bootargs"):
        "debug_and_test_bootargs",
    ("/soc@0/serial@88e0000", "status"):
        "eud_debug_route",
    ("/soc@0/spmi@c440000/pmic@2/typec@1500", "status"):
        "charging_usb_input_experiment",
    ("/", "qcom,msm-id"): "vendor_compat_fields",
    ("/", "qcom,board-id"): "vendor_compat_fields",
    ("/", "oppo,dtsi_no"): "vendor_compat_fields",
}


PHANDLE_CATEGORIES = {
    "/reserved-memory/memory@9ab00000": "camera_icp_experiment",
    "/soc@0/serial@88e0000": "eud_debug_route",
    "/soc@0/spmi@c440000/pmic@2/typec@1500":
        "charging_usb_input_experiment",
    "/soc@0/usb@a6f8800/usb@a600000": "usb_controller_linkage",
}


def category_for_node(path: str) -> str | None:
    if path.startswith("/reserved-memory/reservation-icp-"):
        return "camera_icp_experiment"
    return EXACT_NODE_CATEGORIES.get(path)


def category_for_property(path: str, name: str) -> str | None:
    if path.startswith("/reserved-memory/reservation-icp-"):
        return "camera_icp_experiment"
    return EXACT_PROPERTY_CATEGORIES.get((path, name))


def add_item(items, category, kind, item):
    if category is None:
        items["unclassified"].append({"kind": kind, **item})
        return
    items[category].append({"kind": kind, **item})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("semantic_diff", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--allow-unclassified",
        action="store_true",
        help="still write the ledger and exit zero if a semantic item is unmatched",
    )
    args = parser.parse_args()

    diff = json.loads(args.semantic_diff.read_text(encoding="utf-8"))
    if diff.get("schema") != SCHEMA:
        raise SystemExit(
            f"unsupported semantic diff schema: {diff.get('schema')!r}; "
            f"expected {SCHEMA!r}"
        )

    items = {category: [] for category in CATEGORY_ORDER}
    items["unclassified"] = []

    for path in diff.get("only_before_nodes", []):
        add_item(items, category_for_node(path), "node_removed", {"path": path})
    for path in diff.get("only_after_nodes", []):
        add_item(items, category_for_node(path), "node_added", {"path": path})

    for item in diff.get("only_before_properties", []):
        add_item(
            items,
            category_for_property(item["path"], item["property"]),
            "property_removed",
            item,
        )
    for item in diff.get("only_after_properties", []):
        add_item(
            items,
            category_for_property(item["path"], item["property"]),
            "property_added",
            item,
        )

    for item in diff.get("only_before_phandle_properties", []):
        add_item(
            items,
            PHANDLE_CATEGORIES.get(item["path"]),
            "phandle_link_removed",
            item,
        )
    for item in diff.get("only_after_phandle_properties", []):
        add_item(
            items,
            PHANDLE_CATEGORIES.get(item["path"]),
            "phandle_link_added",
            item,
        )

    for item in diff.get("changed_properties", []):
        add_item(
            items,
            category_for_property(item["path"], item["property"]),
            "property_changed",
            item,
        )

    categories = []
    classified = 0
    for category in CATEGORY_ORDER:
        meta = CATEGORY_META[category]
        entries = sorted(items[category], key=lambda item: (
            item["kind"], item.get("path", ""), item.get("property", "")
        ))
        classified += len(entries)
        categories.append({
            "id": category,
            **meta,
            "item_count": len(entries),
            "items": entries,
        })

    unclassified = items["unclassified"]
    semantic_count = sum(len(items[category]) for category in CATEGORY_ORDER)
    semantic_count += len(unclassified)
    normalization = diff.get("summary", {})

    ledger = {
        "schema": LEDGER_SCHEMA,
        "input": {
            "semantic_diff": str(args.semantic_diff),
            "semantic_diff_schema": diff.get("schema"),
            "before": diff.get("before"),
            "before_sha256": diff.get("before_sha256"),
            "after": diff.get("after"),
            "after_sha256": diff.get("after_sha256"),
        },
        "baseline": {
            "canonical_os_dtb_is_source_of_truth": True,
            "new_public_abi_items_in_this_diff": 0,
            "statement": (
                "No difference in the deployed DTB is promoted to stable "
                "public hardware ABI by this ledger. The canonical k363 DTB "
                "remains the baseline until an item is separately verified "
                "and frozen."
            ),
        },
        "coverage": {
            "semantic_items": semantic_count,
            "classified_items": classified,
            "unclassified_items": len(unclassified),
            "normalization_context": {
                "phandle_value_only_count": normalization.get(
                    "phandle_value_only_count", 0),
                "reference_normalized_property_count": normalization.get(
                    "reference_normalized_property_count", 0),
            },
        },
        "categories": categories,
        "unclassified": unclassified,
    }

    args.output.write_text(
        json.dumps(ledger, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    if unclassified and not args.allow_unclassified:
        print(
            f"{len(unclassified)} semantic item(s) are not classified; "
            f"see {args.output}",
            file=sys.stderr,
        )
        return 2

    print(
        f"{classified}/{semantic_count} semantic items classified; "
        f"ledger written to {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
