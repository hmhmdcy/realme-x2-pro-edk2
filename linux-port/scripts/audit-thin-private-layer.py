#!/usr/bin/env python3
"""Audit the remaining RMX1931 board-private kernel surface."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys


PLATFORM_BASE = "09455be5a5c3421019315de48a32c9ded91d0030"
PLATFORM_HEAD = "824dc0a56143d8bf1cc1d20adb877abced48b336"


FORBIDDEN_PATTERNS = {
    "private_ioctl": re.compile(r"\b(?:unlocked_ioctl|compat_ioctl)\b"),
    "user_copy": re.compile(r"\b(?:copy_from_user|copy_to_user)\b"),
    "ioctl_command": re.compile(r"\b_I[OWR]\("),
    "android_api": re.compile(
        r"(?:CONFIG_ANDROID|\bandroid_|#\s*include\s*<[^>]*android)"
    ),
    "binder_api": re.compile(r"\b(?:binder_|BINDER_)"),
}


CODE_FILES = [
    {
        "path": "drivers/power/supply/mp2650_charger.c",
        "role": "MP2650 charger power_supply driver",
        "standard_api": ["linux/power_supply.h",
                         "devm_power_supply_register",
                         "struct power_supply_desc"],
        "private_reason": (
            "the board charger has no complete in-tree driver; the driver "
            "exposes standard power_supply properties only"
        ),
        "upstream_path": "standalone power_supply driver",
    },
    {
        "path": "drivers/gpu/drm/panel/panel-samsung-sofef03f.c",
        "role": "Samsung SOFEF03F DSI panel",
        "standard_api": ["drm/drm_panel.h", "devm_drm_panel_alloc",
                         "struct drm_panel"],
        "private_reason": (
            "panel power, DSC and 60/90 Hz command sequences are board-specific; "
            "the implementation uses the standard DRM panel model"
        ),
        "upstream_path": "standalone DRM panel driver",
    },
    {
        "path": "drivers/net/ipa/data/ipa_data-v4.1.c",
        "role": "SM8150 IPA v4.1 endpoint and resource data",
        "standard_api": ["ipa_data.h", "ipa_data_v4_1", "struct ipa_data"],
        "private_reason": (
            "the current mainline IPA data lacks this SM8150 v4.1 table"
        ),
        "upstream_path": "upstream SoC IPA data",
    },
    {
        "path": "drivers/net/ipa/reg/ipa_reg-v4.1.c",
        "role": "SM8150 IPA v4.1 register layout",
        "standard_api": ["ipa_reg.h", "ipa_regs_v4_1", "struct regs"],
        "private_reason": (
            "the current mainline IPA register description lacks this SoC"
        ),
        "upstream_path": "upstream SoC IPA register data",
    },
    {
        "path": "drivers/phy/qualcomm/phy-qcom-snps-femto-v2-window.h",
        "role": "USB2 PHY window coordination interface",
        "standard_api": ["struct phy", "qcom_snps_hsphy_window_client_ops"],
        "private_reason": (
            "the standard PHY driver needs a small window client interface for "
            "the board USB controller"
        ),
        "upstream_path": "merge with the common SNPS Femto PHY driver",
    },
    {
        "path": "drivers/gpu/drm/msm/msm_dsi_trace.h",
        "role": "MSM DSI diagnostic tracepoints",
        "standard_api": ["linux/tracepoint.h", "TRACE_EVENT"],
        "private_reason": "diagnostic tracepoints only; no hardware transport API",
        "upstream_path": "generic MSM DSI tracing",
    },
    {
        "path": "include/trace/events/drm_panel.h",
        "role": "generic DRM panel diagnostic tracepoint",
        "standard_api": ["linux/tracepoint.h", "TRACE_EVENT"],
        "private_reason": "diagnostic tracepoint only; no hardware transport API",
        "upstream_path": "generic DRM tracing",
    },
    {
        "path": "sound/soc/qcom/samurai-audio.c",
        "role": "board ASoC machine driver",
        "standard_api": ["linux/platform_device.h", "sound/soc.h",
                         "devm_snd_soc_register_card"],
        "private_reason": (
            "SM8150/Q6AFE to WCD9340 and MAX98937 board routing, DAI clocks "
            "and headset-jack wiring"
        ),
        "upstream_path": "generic board machine driver or upstream DT routing",
    },
    {
        "path": "sound/soc/codecs/max98937-samurai.c",
        "role": "speaker amplifier codec driver",
        "standard_api": ["linux/i2c.h", "sound/soc.h",
                         "devm_snd_soc_register_component"],
        "private_reason": (
            "MAX98937 is not covered by the in-tree MAX98927 driver; register "
            "map, DAPM and mute sequence are hardware-specific"
        ),
        "upstream_path": "standalone ASoC codec driver",
    },
    {
        "path": "drivers/input/misc/aw8697-samurai.c",
        "role": "AW8697 haptic input device",
        "standard_api": ["linux/input.h", "input_ff_create_memless",
                         "input_register_device"],
        "private_reason": (
            "AW8697 uses a different register map from the in-tree AW86927; "
            "the board driver exposes only standard input force feedback"
        ),
        "upstream_path": "standalone input/ff driver",
    },
    {
        "path": "drivers/misc/samurai-sensor-power.c",
        "role": "SLPI sensor rail sequencer",
        "standard_api": ["linux/remoteproc.h", "struct rproc_subdev",
                         "devm_regulator_get"],
        "private_reason": (
            "two board rails must follow SLPI prepare/unprepare ordering; "
            "the implementation is a standard remoteproc subdevice"
        ),
        "upstream_path": "generic remoteproc supply-sequence helper if warranted",
    },
    {
        "path": "drivers/misc/samurai-sensor-power-seq.h",
        "role": "sensor rail sequencer interface",
        "standard_api": ["struct samurai_power_state", "samurai_power_ops"],
        "private_reason": "minimal state structure shared by the board sequencer",
        "upstream_path": "merge into the sequencer if upstreamed",
    },
    {
        "path": "drivers/media/i2c/lc898219xi.c",
        "role": "wide-camera VCM lens driver",
        "standard_api": ["struct v4l2_subdev", "media/v4l2-device.h"],
        "private_reason": (
            "LC898219XI is not represented by a complete in-tree lens driver"
        ),
        "upstream_path": "standalone V4L2 lens subdevice driver",
    },
    {
        "path": "drivers/media/i2c/s5kgw1.c",
        "role": "wide-camera sensor driver",
        "standard_api": ["struct v4l2_subdev", "media/v4l2-cci.h"],
        "private_reason": (
            "S5KGW1 needs RAW10 C-PHY modes, controls and OPP tables for this "
            "module; no complete in-tree match exists"
        ),
        "upstream_path": "standalone V4L2 sensor subdevice driver",
    },
]


DATA_FILES = [
    {
        "path": "Documentation/devicetree/bindings/display/panel/samsung,sofef03f-m.yaml",
        "role": "public DT binding for the SOFEF03F panel",
    },
    {
        "path": "Documentation/devicetree/bindings/power/supply/mps,mp2650.yaml",
        "role": "public DT binding for the MP2650 charger",
    },
    {
        "path": "arch/arm64/boot/dts/qcom/imx319.dtsi",
        "role": "IMX319 sensor module description",
    },
    {
        "path": "drivers/media/i2c/imx319-222mhz-tables.h",
        "role": "IMX319 sensor mode register data",
    },
    {
        "path": "drivers/media/i2c/s5k3m5-oem-tables.h",
        "role": "S5K3M5 sensor mode register data",
    },
    {
        "path": "drivers/media/i2c/s5kgw1-tables.h",
        "role": "S5KGW1 sensor mode and OPP register data",
    },
    {
        "path": "arch/arm64/boot/dts/qcom/sm8150-samurai-common.dtsi",
        "role": "board wiring, regulators, buses and peripheral nodes",
    },
    {
        "path": "arch/arm64/boot/dts/qcom/sm8150-samurai.dts",
        "role": "production OS-facing board wrapper",
    },
    {
        "path": "arch/arm64/boot/dts/qcom/s5k3m5-samurai.dtsi",
        "role": "S5K3M5 module description",
    },
    {
        "path": "arch/arm64/boot/dts/qcom/s5kgw1-samurai.dtsi",
        "role": "S5KGW1 module description",
    },
    {
        "path": "arch/arm64/boot/dts/qcom/samurai-sensor-power-data.dtsi",
        "role": "sensor rail mapping consumed by the remoteproc subdevice",
    },
]


ALLOWED_LEGACY_SURFACES = {
    "drivers/misc/samurai-sensor-power.c": [
        "DEVICE_ATTR_RO(state)",
    ],
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(root: Path, *argv: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(root), *argv],
        capture_output=True,
        text=True,
        check=False,
    )


def audit_platform_patch(root: Path) -> dict:
    names = git(
        root,
        "diff",
        "--name-only",
        f"{PLATFORM_BASE}..{PLATFORM_HEAD}",
    )
    diff = git(
        root,
        "diff",
        f"{PLATFORM_BASE}..{PLATFORM_HEAD}",
        "--",
        "*.c",
        "*.h",
    )
    findings = []
    if diff.returncode == 0:
        for line in diff.stdout.splitlines():
            if not line.startswith("+") or line.startswith("+++"):
                continue
            for name, pattern in FORBIDDEN_PATTERNS.items():
                if pattern.search(line[1:]):
                    findings.append({
                        "kind": name,
                        "text": line[1:].strip(),
                    })
    return {
        "base": PLATFORM_BASE,
        "head": PLATFORM_HEAD,
        "changed_files": (
            len([line for line in names.stdout.splitlines() if line])
            if names.returncode == 0 else None
        ),
        "added_c_h_forbidden_findings": findings,
    }


def file_record(root: Path, entry: dict) -> dict:
    path = root / entry["path"]
    if not path.is_file():
        return {
            **entry,
            "exists": False,
            "passed": False,
            "error": "missing",
        }
    data = path.read_bytes()
    text = data.decode("utf-8", "replace")
    tracked = git(root, "ls-files", "--error-unmatch", entry["path"])
    status = git(root, "status", "--short", "--", entry["path"])
    return {
        **entry,
        "exists": True,
        "bytes": len(data),
        "lines": len(text.splitlines()),
        "sha256": sha256(data),
        "tracked_in_head": tracked.returncode == 0,
        "working_tree_status": status.stdout.strip(),
    }


def audit_code_file(root: Path, entry: dict) -> dict:
    record = file_record(root, entry)
    if not record["exists"]:
        return record
    text = (root / entry["path"]).read_text(
        encoding="utf-8", errors="replace")
    findings = []
    for name, pattern in FORBIDDEN_PATTERNS.items():
        for line_number, line in enumerate(text.splitlines(), 1):
            if pattern.search(line):
                findings.append({
                    "kind": name,
                    "line": line_number,
                    "text": line.strip(),
                })
    missing_api = [
        token for token in entry["standard_api"]
        if token not in text
    ]
    legacy = []
    for marker in ALLOWED_LEGACY_SURFACES.get(entry["path"], []):
        if marker in text:
            legacy.append(marker)
    unexpected_attributes = [
        match.group(0)
        for match in re.finditer(
            r"\bDEVICE_ATTR(?:_RO|_WO|_RW)?\(\w+\)", text)
        if match.group(0) not in ALLOWED_LEGACY_SURFACES.get(entry["path"], [])
    ]
    record.update({
        "forbidden_findings": findings,
        "missing_standard_api_tokens": missing_api,
        "allowed_legacy_surfaces": legacy,
        "unexpected_legacy_surfaces": unexpected_attributes,
        "passed": not missing_api and not unexpected_attributes,
    })
    return record


def audit_data_file(root: Path, entry: dict) -> dict:
    record = file_record(root, entry)
    record["passed"] = bool(record["exists"])
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--kernel-root",
        type=Path,
        default=Path("/home/cy122/standard-arm64-v7.3.1"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "/mnt/e/edk2-samurai-out/standard-arm64-v7.3.1/"
            "thin-private-layer-audit.json"
        ),
    )
    args = parser.parse_args()
    root = args.kernel_root.resolve()
    if not (root / "Kbuild").is_file():
        parser.error(f"not a Linux source tree: {root}")

    head = git(root, "rev-parse", "HEAD")
    code = [audit_code_file(root, entry) for entry in CODE_FILES]
    data = [audit_data_file(root, entry) for entry in DATA_FILES]
    all_records = code + data
    forbidden = [
        {
            "path": record["path"],
            **finding,
        }
        for record in code
        for finding in record.get("forbidden_findings", [])
    ]
    api_failures = [
        {
            "path": record["path"],
            "missing": record["missing_standard_api_tokens"],
        }
        for record in code
        if record.get("missing_standard_api_tokens")
    ]
    legacy_failures = [
        {
            "path": record["path"],
            "unexpected": record["unexpected_legacy_surfaces"],
        }
        for record in code
        if record.get("unexpected_legacy_surfaces")
    ]
    missing = [record["path"] for record in all_records if not record["exists"]]
    platform_patch = audit_platform_patch(root)
    allowed_legacy = [
        {
            "path": record["path"],
            "surfaces": record["allowed_legacy_surfaces"],
        }
        for record in code
        if record.get("allowed_legacy_surfaces")
    ]
    report = {
        "schema": "samurai-thin-private-layer-audit-v1",
        "kernel_root": str(root),
        "kernel_head": head.stdout.strip() if head.returncode == 0 else None,
        "code_files": code,
        "data_files": data,
        "platform_patch_diff": platform_patch,
        "summary": {
            "code_file_count": len(code),
            "data_file_count": len(data),
            "code_bytes": sum(record.get("bytes", 0) for record in code),
            "data_bytes": sum(record.get("bytes", 0) for record in data),
            "largest_code_file": max(
                (
                    (record["bytes"], record["path"])
                    for record in code
                    if record["exists"]
                ),
                default=(0, None),
            )[1],
            "missing_files": missing,
            "forbidden_private_api_findings": forbidden,
            "missing_standard_api_failures": api_failures,
            "unexpected_legacy_surface_failures": legacy_failures,
            "allowed_legacy_surfaces": allowed_legacy,
            "platform_patch_changed_files": platform_patch["changed_files"],
            "platform_patch_forbidden_added_lines": (
                platform_patch["added_c_h_forbidden_findings"]
            ),
        },
        "scope": (
            "Static inventory and API-boundary audit of the remaining board-"
            "private Linux source and data. It proves the listed files do not "
            "open private ioctl/user-copy entry points and retain their expected "
            "standard subsystem markers. It does not prove upstream acceptance "
            "or runtime correctness."
        ),
    }
    report["passed"] = (
        not missing
        and not forbidden
        and not api_failures
        and not legacy_failures
        and not platform_patch["added_c_h_forbidden_findings"]
        and all(record.get("passed") for record in all_records)
    )
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8")
    sys.stdout.write(text)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
