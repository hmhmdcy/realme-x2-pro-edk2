#!/usr/bin/env python3
"""Build the offline samurai experiment DTB and optionally compare it."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command: list[str], stdout_path: Path, stderr_path: Path) -> dict:
    completed = subprocess.run(
        command,
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
        "returncode": completed.returncode,
        "stdout": str(stdout_path),
        "stderr": str(stderr_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kernel-root", required=True, type=Path)
    parser.add_argument("--dtc", required=True, type=Path)
    parser.add_argument(
        "--wrapper",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "dts"
        / "experiments"
        / "sm8150-samurai-experiment-os.dts",
    )
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument(
        "--compare",
        type=Path,
        help="optional deployed DTB; emit a semantic diff against the build",
    )
    parser.add_argument("--gcc", default="gcc")
    args = parser.parse_args()

    kernel_root = args.kernel_root.resolve()
    dtc = args.dtc.resolve()
    wrapper = args.wrapper.resolve()
    output_dir = args.output_dir.resolve()
    qcom = kernel_root / "arch/arm64/boot/dts/qcom"
    include_prefixes = kernel_root / "scripts/dtc/include-prefixes"
    split_dir = wrapper.parents[1] / "split-ba61"
    experiments_dir = wrapper.parent
    for path in (kernel_root, dtc, wrapper, qcom, include_prefixes, split_dir):
        if not path.exists():
            raise SystemExit(f"missing input: {path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    preprocessed = output_dir / "experiment.dts.tmp"
    output_dtb = output_dir / "sm8150-samurai-experiment-os.dtb"

    commands = []
    commands.append(run(
        [
            args.gcc,
            "-E",
            f"-Wp,-MMD,{output_dir / 'experiment.pre.tmp'}",
            "-nostdinc",
            "-I",
            str(qcom),
            "-I",
            str(include_prefixes),
            "-undef",
            "-D__DTS__",
            "-x",
            "assembler-with-cpp",
            "-o",
            str(preprocessed),
            str(wrapper),
        ],
        output_dir / "cpp.stdout",
        output_dir / "cpp.stderr",
    ))
    commands.append(run(
        [
            str(dtc),
            "-o",
            str(output_dtb),
            "-b",
            "0",
            "-i",
            str(experiments_dir),
            "-i",
            str(split_dir),
            "-i",
            str(qcom),
            "-i",
            str(include_prefixes),
            "-Wno-unique_unit_address",
            "-Wno-unit_address_vs_reg",
            "-Wno-avoid_unnecessary_addr_size",
            "-Wno-alias_paths",
            "-Wno-interrupt_map",
            "-Wno-simple_bus_reg",
            str(preprocessed),
        ],
        output_dir / "dtc.stdout",
        output_dir / "dtc.stderr",
    ))

    result = {
        "schema": "samurai-experiment-dtb-build-v1",
        "passed": True,
        "policy": (
            "offline build of the selected DTS wrapper from the locked "
            "source; not a runtime activation"
        ),
        "inputs": {
            "kernel_root": str(kernel_root),
            "wrapper": str(wrapper),
            "wrapper_sha256": sha256(wrapper),
            "dtc": str(dtc),
            "dtc_sha256": sha256(dtc),
        },
        "commands": commands,
        "output": {
            "path": str(output_dtb),
            "sha256": sha256(output_dtb),
            "bytes": output_dtb.stat().st_size,
            "preprocessed_dts": str(preprocessed),
        },
    }

    if args.compare:
        compare = args.compare.resolve()
        diff_json = output_dir / "deployed-vs-source-reconstruction.json"
        diff_script = Path(__file__).resolve().parent / "diff-dtb.py"
        commands.append(run(
            [
                sys.executable,
                str(diff_script),
                str(compare),
                str(output_dtb),
                "--output",
                str(diff_json),
            ],
            output_dir / "semantic-diff.stdout",
            output_dir / "semantic-diff.stderr",
        ))
        diff = json.loads(diff_json.read_text(encoding="utf-8"))
        result["comparison"] = {
            "deployed": str(compare),
            "deployed_sha256": sha256(compare),
            "semantic_diff": str(diff_json),
            "semantic_diff_sha256": sha256(diff_json),
            "summary": diff["summary"],
            "changed_properties": diff["changed_properties"],
            "only_before_nodes": diff["only_before_nodes"],
            "only_after_nodes": diff["only_after_nodes"],
            "only_before_properties": diff["only_before_properties"],
            "only_after_properties": diff["only_after_properties"],
            "only_before_phandle_properties": diff[
                "only_before_phandle_properties"],
            "only_after_phandle_properties": diff[
                "only_after_phandle_properties"],
        }

    result_path = output_dir / "build-result.json"
    result_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
