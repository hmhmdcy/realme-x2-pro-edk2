#!/usr/bin/env python3
"""Build DTB-only USB2 Type-C candidates for the RMX1931."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path


DEFAULT_KERNEL_ROOT = Path("/home/cy122/standard-arm64-v7.3.1")
DEFAULT_BUILD_ROOT = Path("/home/cy122/samurai-v731-build")
DEFAULT_OVERLAY_DIR = (
    Path(__file__).resolve().parents[1] / "dts" / "experiments"
)

PROFILES = {
    "sink": {
        "overlay": "usb2-typec-sink.dtso",
        "kind": "typec",
        "output": "sm8150-samurai-usb2-typec-sink.dtb",
        "role_switch": False,
        "kernel_requirements": {
            "CONFIG_TYPEC": ("y",),
            "CONFIG_TYPEC_TCPM": ("y",),
            "CONFIG_TYPEC_QCOM_PMIC": ("y",),
            "CONFIG_REGULATOR_QCOM_USB_VBUS": ("y", "m"),
            "CONFIG_USB_DWC3_GADGET": ("y",),
        },
    },
    "dual": {
        "overlay": "usb2-typec-dual.dtso",
        "kind": "typec",
        "output": "sm8150-samurai-usb2-typec-dual.dtb",
        "role_switch": True,
        "kernel_requirements": {
            "CONFIG_TYPEC": ("y",),
            "CONFIG_TYPEC_TCPM": ("y",),
            "CONFIG_TYPEC_QCOM_PMIC": ("y",),
            "CONFIG_REGULATOR_QCOM_USB_VBUS": ("y", "m"),
            "CONFIG_USB_DWC3_DUAL_ROLE": ("y",),
            "CONFIG_USB_ROLE_SWITCH": ("y",),
            "CONFIG_USB_XHCI_HCD": ("y",),
            "CONFIG_USB_XHCI_PLATFORM": ("y",),
        },
    },
}

DTC_WARNINGS = (
    "-Wno-unique_unit_address",
    "-Wno-unit_address_vs_reg",
    "-Wno-avoid_unnecessary_addr_size",
    "-Wno-alias_paths",
    "-Wno-interrupt_map",
    "-Wno-simple_bus_reg",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(
    command: list[str],
    *,
    stdout_path: Path,
    stderr_path: Path,
    cwd: Path | None = None,
) -> dict:
    completed = subprocess.run(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    stdout_path.write_text(completed.stdout, encoding="utf-8")
    stderr_path.write_text(completed.stderr, encoding="utf-8")
    if completed.returncode:
        raise SystemExit(
            f"command failed ({completed.returncode}): {' '.join(command)}\n"
            f"stderr: {stderr_path}"
        )
    return {
        "argv": command,
        "cwd": str(cwd) if cwd else None,
        "returncode": completed.returncode,
        "stdout": str(stdout_path),
        "stderr": str(stderr_path),
    }


def preprocess(
    gcc: str,
    source: Path,
    output: Path,
    include_prefixes: Path,
) -> list[str]:
    return [
        gcc,
        "-E",
        f"-Wp,-MMD,{output.with_suffix('.pre.tmp')}",
        "-nostdinc",
        "-I",
        str(include_prefixes),
        "-undef",
        "-D__DTS__",
        "-x",
        "assembler-with-cpp",
        "-o",
        str(output),
        str(source),
    ]


def compile_dtb(
    dtc: Path,
    source: Path,
    output: Path,
    *,
    qcom: Path,
    include_prefixes: Path,
    symbols: bool,
) -> list[str]:
    command = [
        str(dtc),
        "-o",
        str(output),
        "-b",
        "0",
        "-i",
        str(qcom),
        "-i",
        str(include_prefixes),
        *DTC_WARNINGS,
    ]
    if symbols:
        command.append("-@")
    command.append(str(source))
    return command


def fdtget_value(
    fdtget: Path,
    dtb: Path,
    node: str,
    prop: str,
    value_type: str,
    output_dir: Path,
    *,
    required: bool = True,
) -> str | None:
    stem = f"{node.strip('/').replace('/', '-')}-{prop}"
    completed = subprocess.run(
        [str(fdtget), "-t", value_type, str(dtb), node, prop],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    (output_dir / f"fdtget-{stem}.stdout").write_text(
        completed.stdout,
        encoding="utf-8",
    )
    (output_dir / f"fdtget-{stem}.stderr").write_text(
        completed.stderr,
        encoding="utf-8",
    )
    if completed.returncode:
        if not required:
            return None
        raise SystemExit(
            f"fdtget failed for {node}:{prop}: {completed.stderr.strip()}"
        )
    return completed.stdout.strip()


def kernel_config_status(
    config_path: Path,
    requirements: dict[str, tuple[str, ...]],
) -> dict:
    text = config_path.read_text(encoding="utf-8")
    status = {}
    missing = []
    for key, allowed in requirements.items():
        match = re.search(rf"^{re.escape(key)}=(.*)$", text, re.MULTILINE)
        actual = match.group(1) if match else "n"
        satisfied = actual in allowed
        status[key] = {
            "actual": actual,
            "allowed": list(allowed),
            "satisfied": satisfied,
        }
        if not satisfied:
            missing.append(key)
    return {
        "config": str(config_path),
        "config_sha256": sha256(config_path),
        "requirements": status,
        "missing": missing,
        "satisfied": not missing,
    }


def verify_merged_dtb(
    dtc: Path,
    fdtget: Path,
    merged_dtb: Path,
    output_dir: Path,
    profile: str,
) -> dict:
    merged_dts = output_dir / "merged.dts"
    run(
        [str(dtc), "-I", "dtb", "-O", "dts", "-o", str(merged_dts),
         str(merged_dtb)],
        stdout_path=output_dir / "decode.stdout",
        stderr_path=output_dir / "decode.stderr",
    )

    typec = "/soc@0/spmi@c440000/pmic@2/typec@1500"
    vbus = "/soc@0/spmi@c440000/pmic@2/usb-vbus-regulator@1100"
    connector = f"{typec}/connector"
    connector_ep = f"{connector}/ports/port@0/endpoint"
    usb = "/soc@0/usb@a600000"
    usb_ep = f"{usb}/ports/port@0/endpoint"

    checks = {
        "typec_status": fdtget_value(
            fdtget, merged_dtb, typec, "status", "s", output_dir,
        ),
        "vbus_status": fdtget_value(
            fdtget, merged_dtb, vbus, "status", "s", output_dir,
        ),
        "power_role": fdtget_value(
            fdtget, merged_dtb, connector, "power-role", "s", output_dir,
        ),
        "data_role": fdtget_value(
            fdtget, merged_dtb, connector, "data-role", "s", output_dir,
        ),
    }
    if checks["typec_status"] != "okay" or checks["vbus_status"] != "okay":
        raise SystemExit("merged DTB verification failed: Type-C/VBUS disabled")
    expected_roles = {
        "sink": ("sink", "device"),
        "dual": ("dual", "dual"),
    }
    if (checks["power_role"], checks["data_role"]) != expected_roles[profile]:
        raise SystemExit("merged DTB verification failed: wrong connector roles")

    verification = {
        "passed": True,
        "decoded_dts": str(merged_dts),
        "decoded_dts_sha256": sha256(merged_dts),
        "checks": checks,
    }

    if PROFILES[profile]["role_switch"]:
        checks["role_switch_default_mode"] = fdtget_value(
            fdtget, merged_dtb, usb, "role-switch-default-mode", "s", output_dir,
        )
        if checks["role_switch_default_mode"] != "peripheral":
            raise SystemExit("merged DTB verification failed: wrong default role")
        if fdtget_value(
            fdtget, merged_dtb, usb, "usb-role-switch", "s", output_dir,
            required=False,
        ) is None:
            raise SystemExit("merged DTB verification failed: no usb-role-switch")

        connector_endpoint = {
            "phandle": fdtget_value(
                fdtget, merged_dtb, connector_ep, "phandle", "x", output_dir,
            ),
            "remote": fdtget_value(
                fdtget, merged_dtb, connector_ep, "remote-endpoint", "x", output_dir,
            ),
        }
        dwc3_endpoint = {
            "phandle": fdtget_value(
                fdtget, merged_dtb, usb_ep, "phandle", "x", output_dir,
            ),
            "remote": fdtget_value(
                fdtget, merged_dtb, usb_ep, "remote-endpoint", "x", output_dir,
            ),
        }
        if (
            int(connector_endpoint["remote"], 16) != int(dwc3_endpoint["phandle"], 16)
            or int(dwc3_endpoint["remote"], 16) != int(connector_endpoint["phandle"], 16)
        ):
            raise SystemExit(
                "merged DTB verification failed: HS graph endpoints are not reciprocal"
            )
        verification["hs_graph"] = {
            "connector": connector_endpoint,
            "dwc3": dwc3_endpoint,
        }
    else:
        checks["dr_mode"] = fdtget_value(
            fdtget, merged_dtb, usb, "dr_mode", "s", output_dir,
        )
        if checks["dr_mode"] != "peripheral":
            raise SystemExit("merged DTB verification failed: sink changed dr_mode")
        if fdtget_value(
            fdtget, merged_dtb, usb, "usb-role-switch", "s", output_dir,
            required=False,
        ) is not None:
            raise SystemExit("merged DTB verification failed: sink enabled role switch")

    return verification


def build_profile(
    profile: str,
    *,
    kernel_root: Path,
    base_symbols: Path,
    overlay_dir: Path,
    output_dir: Path,
    gcc: str,
    dtc: Path,
    fdtoverlay: Path,
    fdtput: Path,
    fdtget: Path,
    kernel_config: Path,
) -> dict:
    qcom = kernel_root / "arch/arm64/boot/dts/qcom"
    include_prefixes = kernel_root / "scripts/dtc/include-prefixes"
    profile_spec = PROFILES[profile]
    overlay = overlay_dir / profile_spec["overlay"]
    profile_dir = output_dir / profile
    profile_dir.mkdir(parents=True, exist_ok=True)

    overlay_preprocessed = profile_dir / f"{profile}.dts.tmp"
    overlay_dtbo = profile_dir / f"{profile}.dtbo"
    merged_dtb = profile_dir / profile_spec["output"]

    commands = [
        run(
            preprocess(gcc, overlay, overlay_preprocessed, include_prefixes),
            stdout_path=profile_dir / "overlay-cpp.stdout",
            stderr_path=profile_dir / "overlay-cpp.stderr",
        ),
        run(
            compile_dtb(
                dtc,
                overlay_preprocessed,
                overlay_dtbo,
                qcom=qcom,
                include_prefixes=include_prefixes,
                symbols=True,
            ),
            stdout_path=profile_dir / "overlay-dtc.stdout",
            stderr_path=profile_dir / "overlay-dtc.stderr",
        ),
        run(
            [
                str(fdtoverlay),
                "-i",
                str(base_symbols),
                "-o",
                str(merged_dtb),
                str(overlay_dtbo),
            ],
            stdout_path=profile_dir / "fdtoverlay.stdout",
            stderr_path=profile_dir / "fdtoverlay.stderr",
        ),
        run(
            [str(fdtput), "-r", str(merged_dtb), "/__symbols__"],
            stdout_path=profile_dir / "fdtput.stdout",
            stderr_path=profile_dir / "fdtput.stderr",
        ),
    ]
    for node, prop in profile_spec.get("remove_properties", ()):
        commands.append(
            run(
                [str(fdtput), "-d", str(merged_dtb), node, prop],
                stdout_path=(
                    profile_dir
                    / f"fdtput-{node.strip('/').replace('/', '-')}-{prop}.stdout"
                ),
                stderr_path=(
                    profile_dir
                    / f"fdtput-{node.strip('/').replace('/', '-')}-{prop}.stderr"
                ),
            )
        )

    verification = verify_merged_dtb(
        dtc,
        fdtget,
        merged_dtb,
        profile_dir,
        profile,
    )
    result = {
        "schema": "samurai-usb2-typec-dtb-candidate-v1",
        "profile": profile,
        "passed": True,
        "requires_kernel_config": profile_spec["kernel_requirements"],
        "kernel_config": kernel_config_status(
            kernel_config,
            profile_spec["kernel_requirements"],
        ),
        "policy": (
            "DTB-only offline candidate; no Image, boot partition, NV, "
            "persist, calibration or userdata write"
        ),
        "inputs": {
            "kernel_root": str(kernel_root),
            "overlay": str(overlay),
            "overlay_sha256": sha256(overlay),
            "base_symbols": str(base_symbols),
            "base_symbols_sha256": sha256(base_symbols),
            "dtc": str(dtc),
            "dtc_sha256": sha256(dtc),
            "fdtoverlay": str(fdtoverlay),
            "fdtoverlay_sha256": sha256(fdtoverlay),
            "fdtput": str(fdtput),
            "fdtput_sha256": sha256(fdtput),
            "fdtget": str(fdtget),
            "fdtget_sha256": sha256(fdtget),
        },
        "output": {
            "dtb": str(merged_dtb),
            "dtb_sha256": sha256(merged_dtb),
            "dtb_bytes": merged_dtb.stat().st_size,
            "overlay_dtbo": str(overlay_dtbo),
            "overlay_dtbo_sha256": sha256(overlay_dtbo),
            "overlay_dtbo_bytes": overlay_dtbo.stat().st_size,
        },
        "verification": verification,
        "commands": commands,
    }
    (profile_dir / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kernel-root", type=Path, default=DEFAULT_KERNEL_ROOT)
    parser.add_argument("--build-root", type=Path, default=DEFAULT_BUILD_ROOT)
    parser.add_argument("--overlay-dir", type=Path, default=DEFAULT_OVERLAY_DIR)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument(
        "--profile",
        choices=("sink", "dual", "wake", "all"),
        default="all",
    )
    parser.add_argument("--gcc", default="gcc")
    parser.add_argument("--dtc", type=Path)
    parser.add_argument("--fdtoverlay", type=Path)
    parser.add_argument("--fdtput", type=Path)
    parser.add_argument("--fdtget", type=Path)
    parser.add_argument("--kernel-config", type=Path)
    args = parser.parse_args()

    kernel_root = args.kernel_root.resolve()
    build_root = args.build_root.resolve()
    overlay_dir = args.overlay_dir.resolve()
    output_dir = args.output_dir.resolve()
    dtc = (args.dtc or build_root / "scripts/dtc/dtc").resolve()
    fdtoverlay = (
        args.fdtoverlay or build_root / "scripts/dtc/fdtoverlay"
    ).resolve()
    fdtput = (
        args.fdtput or Path(shutil.which("fdtput") or "/usr/bin/fdtput")
    ).resolve()
    fdtget = (
        args.fdtget or Path(shutil.which("fdtget") or "/usr/bin/fdtget")
    ).resolve()
    kernel_config = (args.kernel_config or build_root / ".config").resolve()

    base_dts = kernel_root / "arch/arm64/boot/dts/qcom/sm8150-samurai.dts"
    qcom = kernel_root / "arch/arm64/boot/dts/qcom"
    include_prefixes = kernel_root / "scripts/dtc/include-prefixes"
    for path in (
        base_dts,
        qcom,
        include_prefixes,
        overlay_dir,
        dtc,
        fdtoverlay,
        fdtput,
        fdtget,
        kernel_config,
    ):
        if not path.exists():
            raise SystemExit(f"missing input: {path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    base_preprocessed = output_dir / "sm8150-samurai.dts.tmp"
    base_symbols = output_dir / "sm8150-samurai-symbols.dtb"
    base_clean = output_dir / "sm8150-samurai-base-clean.dtb"

    commands = []
    commands.append(run(
        preprocess(args.gcc, base_dts, base_preprocessed, include_prefixes),
        stdout_path=output_dir / "base-cpp.stdout",
        stderr_path=output_dir / "base-cpp.stderr",
    ))
    commands.append(run(
        compile_dtb(
            dtc,
            base_preprocessed,
            base_symbols,
            qcom=qcom,
            include_prefixes=include_prefixes,
            symbols=True,
        ),
        stdout_path=output_dir / "base-dtc.stdout",
        stderr_path=output_dir / "base-dtc.stderr",
    ))
    shutil.copyfile(base_symbols, base_clean)
    commands.append(run(
        [
            str(fdtput),
            "-r",
            str(base_clean),
            "/__symbols__",
        ],
        stdout_path=output_dir / "base-fdtput.stdout",
        stderr_path=output_dir / "base-fdtput.stderr",
    ))

    profiles = tuple(PROFILES) if args.profile == "all" else (args.profile,)
    results = [
        build_profile(
            profile,
            kernel_root=kernel_root,
            base_symbols=base_symbols,
            overlay_dir=overlay_dir,
            output_dir=output_dir,
            gcc=args.gcc,
            dtc=dtc,
            fdtoverlay=fdtoverlay,
            fdtput=fdtput,
            fdtget=fdtget,
            kernel_config=kernel_config,
        )
        for profile in profiles
    ]

    manifest = {
        "schema": "samurai-usb2-typec-build-v1",
        "passed": True,
        "base_dts": str(base_dts),
        "base_dts_sha256": sha256(base_dts),
        "base_dtb_symbols": str(base_symbols),
        "base_dtb_symbols_sha256": sha256(base_symbols),
        "base_dtb_symbols_bytes": base_symbols.stat().st_size,
        "base_dtb_clean": str(base_clean),
        "base_dtb_clean_sha256": sha256(base_clean),
        "base_dtb_clean_bytes": base_clean.stat().st_size,
        "profiles": results,
        "commands": commands,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
