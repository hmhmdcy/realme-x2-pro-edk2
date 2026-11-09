#!/usr/bin/env python3
"""Exercise the Samurai DTB contract gate against known offline artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
DEFAULT_OUT = Path(
    os.environ.get(
        "EDK2_SAMURAI_OUT",
        "/mnt/e/edk2-samurai-out",
    )
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_check(
    checker: Path,
    manifest: Path,
    baseline: Path,
    candidate: Path,
    output: Path,
) -> tuple[int, dict]:
    proc = subprocess.run(
        [
            sys.executable,
            str(checker),
            "--manifest",
            str(manifest),
            "--baseline",
            str(baseline),
            "--candidate",
            str(candidate),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
    )
    try:
        report = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"checker did not emit JSON for {candidate}: {exc}\n"
            f"stdout={proc.stdout}\nstderr={proc.stderr}"
        ) from exc
    return proc.returncode, report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--summary", type=Path)
    parser.add_argument("--work-dir", type=Path)
    args = parser.parse_args()

    checker = REPO / "linux-port/scripts/check-dtb-contract.py"
    manifest = REPO / "linux-port/dts/samurai-dt-v1-abi.json"
    baseline = (
        args.out
        / "standard-arm64-v731/camera-final-boot/"
        "sm8150-samurai-v731-camera.dtb"
    )
    experiment = (
        args.out / "layer-adaptation-20261105/experiment-dtb-build/"
        "sm8150-samurai-experiment-os.dtb"
    )
    vendor = (
        args.out / "layer-adaptation-20261105/dtb-rebuild-ba61/"
        "arch/arm64/boot/dts/qcom/sm8150-samurai-vendor.dtb"
    )
    flash_led = (
        args.out
        / "standard-arm64-v731/flash-led-v4l2-20261109/"
        "sm8150-samurai-v731-flash-led-v4l2.dtb"
    )

    expected_hashes = {
        baseline: "3799ec6c7d3e0c67a657859a37b2fe147fa21a9dedc84d49c8eb83fd8debc805",
        experiment: "c582dd7cf36e9a3796533674edddea1fc55a30f44b605bf9e8161b015d77a64f",
        vendor: "dcdd74ec903520c7023fa28badcb293b2e4e26ee5bac639497c63d53536b2c8d",
        flash_led: "b244b3f10a14811dca2e808efa8c840f432cac69020e66b60eba97d02794a18e",
    }
    work_dir = args.work_dir or Path(tempfile.mkdtemp(prefix="samurai-dtb-contract-"))
    work_dir.mkdir(parents=True, exist_ok=True)
    summary_path = args.summary or args.out / "l2-abi-contract/test-summary.json"
    fdtput = shutil.which("fdtput")
    additive = work_dir / "dynamic-chosen-additive.dtb"
    additive_ready = False
    additive_error = None
    if fdtput is not None:
        shutil.copyfile(baseline, additive)
        proc = subprocess.run(
            [
                fdtput,
                "-t",
                "s",
                str(additive),
                "/chosen",
                "linux,contract-test",
                "allowed",
            ],
            capture_output=True,
            text=True,
        )
        additive_ready = proc.returncode == 0
        if not additive_ready:
            additive_error = proc.stderr.strip()

    cases = [
        {
            "id": "baseline_identity",
            "baseline": baseline,
            "candidate": baseline,
            "expected_passed": True,
            "expected_codes": [],
        },
        {
            "id": "dynamic_chosen_property_accepted",
            "baseline": baseline,
            "candidate": additive,
            "expected_passed": True,
            "expected_codes": [],
        },
        {
            "id": "flash_led_v4l2_additive_accepted",
            "baseline": baseline,
            "candidate": flash_led,
            "expected_passed": True,
            "expected_codes": [],
        },
        {
            "id": "experiment_profile_rejected",
            "baseline": baseline,
            "candidate": experiment,
            "expected_passed": False,
            "expected_codes": [
                "forbidden_compatible",
                "forbidden_root_property",
                "reserved_memory_node_added",
            ],
        },
        {
            "id": "vendor_dtb_rejected_as_os",
            "baseline": baseline,
            "candidate": vendor,
            "expected_passed": False,
            "expected_codes": [
                "forbidden_root_property",
                "semantic_property_added",
            ],
        },
    ]

    results = []
    failures = []
    for case in cases:
        case_id = case["id"]
        if case_id == "dynamic_chosen_property_accepted" and not additive_ready:
            results.append({
                "id": case_id,
                "status": "skipped",
                "reason": (
                    "fdtput is not installed"
                    if fdtput is None
                    else f"fdtput failed: {additive_error}"
                ),
            })
            continue
        for path, expected_hash in expected_hashes.items():
            if not path.is_file():
                failures.append({
                    "case": case_id,
                    "error": "artifact_missing",
                    "path": str(path),
                })
                break
            actual_hash = digest(path)
            if actual_hash != expected_hash:
                failures.append({
                    "case": case_id,
                    "error": "artifact_hash_mismatch",
                    "path": str(path),
                    "expected": expected_hash,
                    "actual": actual_hash,
                })
                break
        else:
            report_path = work_dir / f"{case_id}.json"
            rc, report = run_check(
                checker,
                manifest,
                case["baseline"],
                case["candidate"],
                report_path,
            )
            codes = sorted({item["code"] for item in report.get("failures", [])})
            passed = bool(report.get("passed"))
            if passed != case["expected_passed"]:
                failures.append({
                    "case": case_id,
                    "error": "unexpected_pass_fail",
                    "expected_passed": case["expected_passed"],
                    "actual_passed": passed,
                })
            missing_codes = [
                code for code in case["expected_codes"] if code not in codes
            ]
            if missing_codes:
                failures.append({
                    "case": case_id,
                    "error": "expected_failure_codes_missing",
                    "missing": missing_codes,
                    "actual_codes": codes,
                })
            if (rc == 0) != case["expected_passed"]:
                failures.append({
                    "case": case_id,
                    "error": "unexpected_exit_code",
                    "expected_passed": case["expected_passed"],
                    "exit_code": rc,
                })
            results.append({
                "id": case_id,
                "baseline": str(case["baseline"]),
                "baseline_sha256": digest(case["baseline"]),
                "candidate": str(case["candidate"]),
                "candidate_sha256": digest(case["candidate"]),
                "expected_passed": case["expected_passed"],
                "actual_passed": passed,
                "exit_code": rc,
                "failure_codes": codes,
                "report": str(report_path),
                "report_sha256": digest(report_path),
            })

    bad_ufs = work_dir / "bad-ufs-lanes.dtb"
    shutil.copyfile(baseline, bad_ufs)
    if fdtput is None:
        results.append({
            "id": "stable_ufs_property_rejected",
            "status": "skipped",
            "reason": "fdtput is not installed",
        })
    else:
        proc = subprocess.run(
            [
                fdtput,
                "-t",
                "x",
                str(bad_ufs),
                "/soc@0/ufshc@1d84000",
                "lanes-per-direction",
                "1",
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            failures.append({
                "case": "stable_ufs_property_rejected",
                "error": "fdtput_failed",
                "stderr": proc.stderr.strip(),
            })
        else:
            report_path = work_dir / "stable_ufs_property_rejected.json"
            rc, report = run_check(
                checker,
                manifest,
                baseline,
                bad_ufs,
                report_path,
            )
            codes = sorted({item["code"] for item in report.get("failures", [])})
            expected_codes = [
                "stable_property_changed",
                "semantic_property_changed",
            ]
            missing_codes = [code for code in expected_codes if code not in codes]
            if report.get("passed") is not False:
                failures.append({
                    "case": "stable_ufs_property_rejected",
                    "error": "changed_stable_property_was_accepted",
                })
            if missing_codes:
                failures.append({
                    "case": "stable_ufs_property_rejected",
                    "error": "expected_failure_codes_missing",
                    "missing": missing_codes,
                    "actual_codes": codes,
                })
            results.append({
                "id": "stable_ufs_property_rejected",
                "baseline": str(baseline),
                "baseline_sha256": digest(baseline),
                "candidate": str(bad_ufs),
                "candidate_sha256": digest(bad_ufs),
                "expected_passed": False,
                "actual_passed": bool(report.get("passed")),
                "exit_code": rc,
                "failure_codes": codes,
                "report": str(report_path),
                "report_sha256": digest(report_path),
            })

    summary = {
        "schema": "samurai-dtb-contract-test-v1",
        "manifest": str(manifest),
        "manifest_sha256": digest(manifest),
        "checker": str(checker),
        "checker_sha256": digest(checker),
        "work_dir": str(work_dir),
        "passed": not failures,
        "cases": results,
        "failures": failures,
        "scope": (
            "Offline contract-gate tests. A pass proves the checker accepts the "
            "known additive DTB and rejects known non-additive/experiment DTBs; "
            "it does not prove runtime boot or hardware behavior."
        ),
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
