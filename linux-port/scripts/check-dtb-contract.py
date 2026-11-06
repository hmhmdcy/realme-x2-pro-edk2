#!/usr/bin/env python3
"""Check an OS-facing Samurai DTB against the machine-readable platform contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import libfdt


MANIFEST_SCHEMA = "samurai-platform-contract-v1"
REPORT_SCHEMA = "samurai-dtb-contract-check-v1"
MISSING = object()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def string_list(value: bytes | None) -> list[str]:
    if not value:
        return []
    return [
        item.decode("utf-8", "replace")
        for item in value.rstrip(b"\0").split(b"\0")
        if item
    ]


def load_nodes(path: Path) -> tuple[dict[str, dict[str, bytes]], bytes]:
    data = path.read_bytes()
    fdt = libfdt.Fdt(data)
    nodes: dict[str, dict[str, bytes]] = {}

    def walk(offset: int, node_path: str) -> None:
        props: dict[str, bytes] = {}
        prop_offset = fdt.first_property_offset(
            offset, quiet=libfdt.QUIET_NOTFOUND)
        while prop_offset >= 0:
            prop = fdt.get_property_by_offset(prop_offset)
            props[prop.name] = bytes(prop)
            prop_offset = fdt.next_property_offset(
                prop_offset, quiet=libfdt.QUIET_NOTFOUND)
        nodes[node_path] = props

        child = fdt.first_subnode(offset, quiet=libfdt.QUIET_NOTFOUND)
        while child >= 0:
            name = fdt.get_name(child)
            walk(child, node_path.rstrip("/") + "/" + name)
            child = fdt.next_subnode(child, quiet=libfdt.QUIET_NOTFOUND)

    walk(0, "/")
    return nodes, data


def direct_children(nodes: dict[str, dict[str, bytes]], parent: str) -> set[str]:
    prefix = parent.rstrip("/") + "/"
    return {
        path for path in nodes
        if path.startswith(prefix) and "/" not in path[len(prefix):]
    }


def compatible_matches(props: dict[str, bytes], compatible: str) -> bool:
    return compatible in string_list(props.get("compatible"))


def selector_matches(
    nodes: dict[str, dict[str, bytes]], selector: dict
) -> list[str]:
    if "path" in selector:
        path = selector["path"]
        if path not in nodes:
            return []
        if "compatible" in selector and not compatible_matches(
                nodes[path], selector["compatible"]):
            return []
        return [path]

    if "compatible" in selector:
        compatible = selector["compatible"]
        return sorted(
            path for path, props in nodes.items()
            if compatible_matches(props, compatible)
        )

    raise ValueError(f"invalid selector: {selector!r}")


def is_dynamic(path: str, dynamic_paths: list[str]) -> bool:
    for base in dynamic_paths:
        if path == base:
            return True
        if path.startswith(base.rstrip("/") + "/"):
            return True
    return False


def add_failure(report: dict, code: str, message: str, **fields) -> None:
    item = {"code": code, "message": message}
    item.update({
        key: value for key, value in fields.items()
        if value is not None
    })
    report["failures"].append(item)


def add_warning(report: dict, code: str, message: str, **fields) -> None:
    item = {"code": code, "message": message}
    item.update({
        key: value for key, value in fields.items()
        if value is not None
    })
    report["warnings"].append(item)


def resolve_one(
    nodes: dict[str, dict[str, bytes]],
    selector: dict,
    label: str,
    side: str,
    report: dict,
) -> str | None:
    try:
        matches = selector_matches(nodes, selector)
    except ValueError as exc:
        add_failure(
            report,
            "invalid_selector",
            str(exc),
            selector=selector,
            side=side,
            resource=label,
        )
        return None

    if not matches:
        add_failure(
            report,
            f"{side}_selector_not_found",
            f"{label}: selector did not match a node in the {side} DTB",
            selector=selector,
            side=side,
            resource=label,
        )
        return None
    if len(matches) > 1:
        add_failure(
            report,
            "selector_ambiguous",
            f"{label}: selector matched more than one node",
            selector=selector,
            side=side,
            resource=label,
            matches=matches,
        )
        return None
    return matches[0]


def check_manifest(
    manifest: dict,
    baseline: dict[str, dict[str, bytes]],
    candidate: dict[str, dict[str, bytes]],
    report: dict,
) -> None:
    if manifest.get("schema") != MANIFEST_SCHEMA:
        add_failure(
            report,
            "manifest_schema",
            f"unsupported manifest schema {manifest.get('schema')!r}",
        )
        return

    resources = manifest.get("resources")
    if not isinstance(resources, list) or not resources:
        add_failure(report, "manifest_resources", "manifest has no resource list")
        return

    ids: set[str] = set()
    for resource in resources:
        resource_id = resource.get("id")
        if not resource_id:
            add_failure(report, "manifest_resource_id", "resource has no id")
            continue
        if resource_id in ids:
            add_failure(
                report,
                "manifest_duplicate_resource_id",
                f"duplicate resource id {resource_id!r}",
            )
        ids.add(resource_id)
        if not isinstance(resource.get("required_properties", []), list):
            add_failure(
                report,
                "manifest_required_properties",
                f"{resource_id}: required_properties is not a list",
            )
        if not isinstance(resource.get("stable_properties", []), list):
            add_failure(
                report,
                "manifest_stable_properties",
                f"{resource_id}: stable_properties is not a list",
            )
        alternatives = resource.get("required_any_properties", [])
        if not isinstance(alternatives, list) or not all(
            isinstance(group, list) and group
            and all(isinstance(prop, str) and prop for prop in group)
            for group in alternatives
        ):
            add_failure(
                report,
                "manifest_required_any_properties",
                f"{resource_id}: required_any_properties must be a list "
                "of non-empty string lists",
            )
        if not isinstance(resource.get("selector"), dict):
            add_failure(
                report,
                "manifest_selector",
                f"{resource_id}: selector is not an object",
            )

    for uapi in manifest.get("uapi_contracts", []):
        for resource_id in uapi.get("resource_ids", []):
            if resource_id not in ids:
                add_failure(
                    report,
                    "manifest_uapi_resource",
                    f"UAPI {uapi.get('id')!r} references unknown resource "
                    f"{resource_id!r}",
                )

    root = baseline.get("/", {})
    candidate_root = candidate.get("/", {})
    identity = manifest.get("identity", {})
    expected_compatible = identity.get("root_compatible")
    if expected_compatible is not None:
        for label, props in (("baseline", root), ("candidate", candidate_root)):
            actual = string_list(props.get("compatible"))
            if actual != expected_compatible:
                add_failure(
                    report,
                    "root_compatible_changed",
                    f"{label}: root compatible list does not match the contract",
                    side=label,
                    expected=expected_compatible,
                    actual=actual,
                )

    for key, attr in (("model", "model"), ("chassis_type", "chassis-type")):
        expected = identity.get(key)
        if expected is None:
            continue
        for label, props in (("baseline", root), ("candidate", candidate_root)):
            actual = string_list(props.get(attr))
            actual_value = actual[0] if actual else None
            if actual_value != expected:
                add_failure(
                    report,
                    f"root_{key}_changed",
                    f"{label}: root {attr} does not match the contract",
                    side=label,
                    expected=expected,
                    actual=actual_value,
                )

    forbidden_root = set(identity.get("forbidden_root_properties", []))
    for label, props in (("baseline", root), ("candidate", candidate_root)):
        for prop in sorted(forbidden_root & props.keys()):
            add_failure(
                report,
                "forbidden_root_property",
                f"{label}: OS DTB contains vendor/compat property {prop!r}",
                side=label,
                path="/",
                property=prop,
            )

    forbidden_compatibles = set(manifest.get("forbidden_compatibles", []))
    if forbidden_compatibles:
        for label, nodes in (("baseline", baseline), ("candidate", candidate)):
            for path, props in sorted(nodes.items()):
                matches = forbidden_compatibles & set(
                    string_list(props.get("compatible")))
                for compatible in sorted(matches):
                    add_failure(
                        report,
                        "forbidden_compatible",
                        f"{label}: node uses experiment-only compatible "
                        f"{compatible!r}",
                        side=label,
                        path=path,
                        compatible=compatible,
                    )

    for item in manifest.get("forbidden_properties", []):
        path = item.get("path")
        prop = item.get("property")
        if not path or not prop:
            add_failure(
                report,
                "manifest_forbidden_property",
                "forbidden_properties entry needs path and property",
            )
            continue
        for label, nodes in (("baseline", baseline), ("candidate", candidate)):
            if prop in nodes.get(path, {}):
                add_failure(
                    report,
                    "forbidden_property",
                    f"{label}: forbidden experiment property {prop!r} is present",
                    side=label,
                    path=path,
                    property=prop,
                    reason=item.get("reason"),
                )


def check_resources(
    manifest: dict,
    baseline: dict[str, dict[str, bytes]],
    candidate: dict[str, dict[str, bytes]],
    report: dict,
) -> dict[str, str]:
    resource_paths: dict[str, str] = {}
    checked = 0

    for resource in manifest.get("resources", []):
        resource_id = resource.get("id", "<unnamed>")
        selector = resource.get("selector", {})
        baseline_path = resolve_one(
            baseline, selector, resource_id, "baseline", report)
        candidate_path = resolve_one(
            candidate, selector, resource_id, "candidate", report)
        if baseline_path is None or candidate_path is None:
            continue
        checked += 1
        resource_paths[resource_id] = candidate_path

        if baseline_path != candidate_path:
            add_failure(
                report,
                "resource_path_changed",
                f"{resource_id}: stable node path changed",
                resource=resource_id,
                baseline_path=baseline_path,
                candidate_path=candidate_path,
            )

        before = baseline[baseline_path]
        after = candidate[candidate_path]
        required = resource.get("required_properties", [])
        for prop in required:
            if prop not in before:
                add_failure(
                    report,
                    "baseline_missing_required_property",
                    f"{resource_id}: baseline DTB lacks required property "
                    f"{prop!r}",
                    resource=resource_id,
                    path=baseline_path,
                    property=prop,
                )
            if prop not in after:
                add_failure(
                    report,
                    "resource_property_removed",
                    f"{resource_id}: candidate DTB lacks required property "
                    f"{prop!r}",
                    resource=resource_id,
                    path=candidate_path,
                    property=prop,
                )

        for alternatives in resource.get("required_any_properties", []):
            if not any(prop in before for prop in alternatives):
                add_failure(
                    report,
                    "baseline_missing_required_any_property",
                    f"{resource_id}: baseline DTB lacks all required "
                    f"alternatives {alternatives!r}",
                    resource=resource_id,
                    path=baseline_path,
                    properties=alternatives,
                )
            if not any(prop in after for prop in alternatives):
                add_failure(
                    report,
                    "resource_required_any_property_removed",
                    f"{resource_id}: candidate DTB lacks all required "
                    f"alternatives {alternatives!r}",
                    resource=resource_id,
                    path=candidate_path,
                    properties=alternatives,
                )

        for prop in resource.get("stable_properties", []):
            if before.get(prop, MISSING) != after.get(prop, MISSING):
                add_failure(
                    report,
                    "stable_property_changed",
                    f"{resource_id}: stable property {prop!r} changed",
                    resource=resource_id,
                    path=candidate_path,
                    property=prop,
                )

        for child in resource.get("required_children", []):
            child_path = baseline_path.rstrip("/") + "/" + child
            if child_path not in baseline:
                add_failure(
                    report,
                    "baseline_missing_required_child",
                    f"{resource_id}: baseline DTB lacks child {child!r}",
                    resource=resource_id,
                    path=child_path,
                )
            if child_path not in candidate:
                add_failure(
                    report,
                    "resource_child_removed",
                    f"{resource_id}: candidate DTB lacks child {child!r}",
                    resource=resource_id,
                    path=child_path,
                )

    return resource_paths


def check_reserved_memory(
    manifest: dict,
    baseline: dict[str, dict[str, bytes]],
    candidate: dict[str, dict[str, bytes]],
    report: dict,
) -> int:
    rule = manifest.get("reserved_memory", {})
    parent = rule.get("path", "/reserved-memory")
    if parent not in baseline or parent not in candidate:
        add_failure(
            report,
            "reserved_memory_missing",
            f"reserved-memory node {parent!r} is missing",
        )
        return 0

    base_children = direct_children(baseline, parent)
    cand_children = direct_children(candidate, parent)
    allowed_added = set(rule.get("allowed_added_children", []))
    if not rule.get("allow_additional_nodes", False):
        for path in sorted(cand_children - base_children - allowed_added):
            add_failure(
                report,
                "reserved_memory_node_added",
                "candidate added an unlisted reserved-memory node",
                path=path,
            )
    for path in sorted(base_children - cand_children):
        add_failure(
            report,
            "reserved_memory_node_removed",
            "candidate removed a reserved-memory node",
            path=path,
        )

    stable = rule.get("stable_properties", [])
    checked = 0
    for path in sorted(base_children & cand_children):
        checked += 1
        before = baseline[path]
        after = candidate[path]
        for prop in stable:
            if before.get(prop, MISSING) != after.get(prop, MISSING):
                add_failure(
                    report,
                    "reserved_memory_property_changed",
                    f"reserved-memory property {prop!r} changed",
                    path=path,
                    property=prop,
                )
    return checked


def build_allowed_additive(
    manifest: dict,
    candidate: dict[str, dict[str, bytes]],
    report: dict,
) -> dict[tuple[str, str], dict]:
    allowed: dict[tuple[str, str], dict] = {}
    for item in manifest.get("allowed_additive_properties", []):
        selector = item.get("selector")
        prop = item.get("property")
        if not isinstance(selector, dict) or not prop:
            add_failure(
                report,
                "manifest_allowed_additive",
                "allowed_additive_properties entry needs selector and property",
            )
            continue
        matches = selector_matches(candidate, selector)
        if len(matches) != 1:
            add_failure(
                report,
                "allowed_additive_selector",
                f"allowed additive property {prop!r} selector matched "
                f"{len(matches)} nodes",
                property=prop,
                selector=selector,
            )
            continue
        allowed[(matches[0], prop)] = item
    return allowed


def validate_allowed_property(
    item: dict,
    value: bytes,
    report: dict,
    path: str,
    prop: str,
) -> None:
    expected_u32 = item.get("expected_u32")
    if expected_u32 is not None:
        if len(value) != 4:
            add_failure(
                report,
                "allowed_property_type",
                f"{prop}: expected a 32-bit value, got {len(value)} bytes",
                path=path,
                property=prop,
            )
        else:
            actual = int.from_bytes(value, "big")
            if actual != expected_u32:
                add_failure(
                    report,
                    "allowed_property_value",
                    f"{prop}: value {actual} does not match contract "
                    f"{expected_u32}",
                    path=path,
                    property=prop,
                    expected=expected_u32,
                    actual=actual,
                )

    expected_string = item.get("expected_string")
    if expected_string is not None:
        actual = string_list(value)
        actual_value = actual[0] if actual else None
        if actual_value != expected_string:
            add_failure(
                report,
                "allowed_property_value",
                f"{prop}: string does not match contract",
                path=path,
                property=prop,
                expected=expected_string,
                actual=actual_value,
            )


def load_semantic_diff(
    baseline_path: Path,
    candidate_path: Path,
    diff_json: Path | None,
    report: dict,
) -> dict | None:
    if diff_json is not None:
        try:
            return json.loads(diff_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            add_failure(
                report,
                "semantic_diff_read",
                f"cannot read semantic diff: {exc}",
            )
            return None

    diff_script = Path(__file__).with_name("diff-dtb.py")
    if not diff_script.is_file():
        add_failure(
            report,
            "semantic_diff_tool",
            f"semantic diff tool not found: {diff_script}",
        )
        return None

    proc = subprocess.run(
        [sys.executable, str(diff_script), str(baseline_path), str(candidate_path)],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        add_failure(
            report,
            "semantic_diff_failed",
            "diff-dtb.py failed",
            stderr=proc.stderr.strip(),
        )
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        add_failure(
            report,
            "semantic_diff_json",
            f"diff-dtb.py returned invalid JSON: {exc}",
        )
        return None


def check_semantic_diff(
    diff: dict,
    manifest: dict,
    candidate: dict[str, dict[str, bytes]],
    allowed_additive: dict[tuple[str, str], dict],
    report: dict,
) -> None:
    dynamic_paths = manifest.get("dynamic_paths", [])
    allowed_added_nodes = {
        item if isinstance(item, str) else item.get("path")
        for item in manifest.get("allowed_added_nodes", [])
    }
    allowed_removed_nodes = {
        item if isinstance(item, str) else item.get("path")
        for item in manifest.get("allowed_removed_nodes", [])
    }
    allowed_removed_properties = {
        (item.get("path"), item.get("property"))
        for item in manifest.get("allowed_removed_properties", [])
    }
    allowed_changed_properties = {
        (item.get("path"), item.get("property"))
        for item in manifest.get("allowed_changed_properties", [])
    }

    for path in diff.get("only_before_nodes", []):
        if is_dynamic(path, dynamic_paths) or path in allowed_removed_nodes:
            continue
        add_failure(
            report,
            "semantic_node_removed",
            "candidate removed a node",
            path=path,
        )

    for path in diff.get("only_after_nodes", []):
        if is_dynamic(path, dynamic_paths) or path in allowed_added_nodes:
            continue
        add_failure(
            report,
            "semantic_node_added",
            "candidate added an unlisted node",
            path=path,
        )

    for item in diff.get("only_before_properties", []):
        path = item.get("path", "")
        prop = item.get("property", "")
        if is_dynamic(path, dynamic_paths):
            continue
        if (path, prop) in allowed_removed_properties:
            continue
        add_failure(
            report,
            "semantic_property_removed",
            "candidate removed a property",
            path=path,
            property=prop,
        )

    for item in diff.get("only_after_properties", []):
        path = item.get("path", "")
        prop = item.get("property", "")
        if is_dynamic(path, dynamic_paths):
            continue
        allowance = allowed_additive.get((path, prop))
        if allowance is not None:
            value = candidate.get(path, {}).get(prop, b"")
            validate_allowed_property(allowance, value, report, path, prop)
            continue
        add_failure(
            report,
            "semantic_property_added",
            "candidate added an unlisted property",
            path=path,
            property=prop,
        )

    for item in diff.get("changed_properties", []):
        path = item.get("path", "")
        prop = item.get("property", "")
        if is_dynamic(path, dynamic_paths):
            continue
        if (path, prop) in allowed_changed_properties:
            continue
        add_failure(
            report,
            "semantic_property_changed",
            "candidate changed a property value",
            path=path,
            property=prop,
            before=item.get("before"),
            after=item.get("after"),
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--diff-json", type=Path)
    args = parser.parse_args()

    manifest_bytes = args.manifest.read_bytes()
    try:
        manifest = json.loads(manifest_bytes)
    except json.JSONDecodeError as exc:
        print(f"invalid manifest JSON: {exc}", file=sys.stderr)
        return 2

    baseline_nodes, baseline_bytes = load_nodes(args.baseline)
    candidate_nodes, candidate_bytes = load_nodes(args.candidate)

    report = {
        "schema": REPORT_SCHEMA,
        "contract": manifest.get("contract"),
        "contract_status": manifest.get("status"),
        "manifest": str(args.manifest),
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "baseline": {
            "path": str(args.baseline),
            "sha256": hashlib.sha256(baseline_bytes).hexdigest(),
            "bytes": len(baseline_bytes),
        },
        "candidate": {
            "path": str(args.candidate),
            "sha256": hashlib.sha256(candidate_bytes).hexdigest(),
            "bytes": len(candidate_bytes),
        },
        "failures": [],
        "warnings": [],
        "summary": {},
        "scope": (
            "Offline DTB ABI check only. It does not prove that the candidate "
            "boots, that drivers bind, or that any SKU/hardware function works."
        ),
    }

    check_manifest(manifest, baseline_nodes, candidate_nodes, report)
    resource_paths = check_resources(
        manifest, baseline_nodes, candidate_nodes, report)
    reserved_memory_checked = check_reserved_memory(
        manifest, baseline_nodes, candidate_nodes, report)
    allowed_additive = build_allowed_additive(
        manifest, candidate_nodes, report)

    diff = load_semantic_diff(
        args.baseline, args.candidate, args.diff_json, report)
    if diff is not None:
        check_semantic_diff(
            diff, manifest, candidate_nodes, allowed_additive, report)

    if str(manifest.get("status", "")).startswith("draft"):
        add_warning(
            report,
            "contract_is_draft",
            "the contract is still a draft; passing this gate is not an ABI freeze",
        )
    if "/chosen" in candidate_nodes and "bootargs" in candidate_nodes["/chosen"]:
        add_warning(
            report,
            "debug_bootargs_present",
            "/chosen/bootargs is present in the OS DTB; it is a startup policy, "
            "not a hardware ABI",
        )
    if baseline_bytes != candidate_bytes and not report["failures"]:
        add_warning(
            report,
            "additive_only_change",
            "candidate differs from baseline but every semantic change is "
            "explicitly allowed by the contract",
        )

    report["summary"] = {
        "resources_declared": len(manifest.get("resources", [])),
        "resources_checked": len(resource_paths),
        "reserved_memory_nodes_checked": reserved_memory_checked,
        "allowed_additive_properties_checked": len(allowed_additive),
        "failures": len(report["failures"]),
        "warnings": len(report["warnings"]),
        "semantic_diff": (
            diff.get("summary") if isinstance(diff, dict) else None
        ),
    }
    report["passed"] = not report["failures"]

    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
