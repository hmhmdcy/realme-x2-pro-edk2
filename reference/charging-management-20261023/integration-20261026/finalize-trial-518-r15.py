"""Finalize and mirror the fixed-5V 1.5A trial without device IO."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tarfile
from pathlib import Path


BASE = Path(__file__).resolve().parent
OUT = Path(r"E:\edk2-samurai-out\charging-management-20261023")
TRIAL = OUT / "charging-integration-trial-20261027-r9-status-precharge-15"
MIRROR = OUT / "charging-integration-trial-20261027-r9-status-precharge-18"
MANIFEST = TRIAL / "manifest.json"
OPERATOR = TRIAL / "fastboot_operator.ps1"
WINDOWS_RESULTS = TRIAL / "r15-mincap-windows.json"
LINUX_RESULTS = TRIAL / "r15-mincap-linux.json"
EXPECTED_TEST_COUNT = 238
REQUIRED_PASSING_TESTS = {
    "test_manifest.ProductionManifestTests."
    "test_manifest_pins_bundled_files_and_real_carriers",
    "test_mp2650_regressions.Mp2650RegressionTests."
    "test_pd_pps_avs_reject_non_five_volt_allowances",
    "test_mp2650_regressions.Mp2650RegressionTests."
    "test_suspend_keeps_only_proven_active_charging",
    "test_mp2650_regressions.Mp2650RegressionTests."
    "test_timeout_boundary_and_auto_never_clear_cycle_timeout",
    "test_trial_suite.PostbootAuditTests."
    "test_audit_rejects_wrong_managed_source_budget",
    "test_trial_suite.PostbootAuditTests."
    "test_audit_rejects_wrong_mp2650_input_limit",
    "test_physical_cycle.PhysicalCycleTests."
    "test_full_hold_accepts_charger_disabled_status",
    "test_physical_cycle.PhysicalCycleTests."
    "test_telemetry_budget_and_active_net_current_are_required",
    "test_physical_wake.PhysicalWakeTests."
    "test_insert_requires_r15_source_tcpm_mp_and_battery_evidence",
    "test_rtc_suspend.RtcSuspendTests."
    "test_healthy_active_charging_resume_passes",
    "test_source_budget.SourceBudgetTests."
    "test_physical_source_cap_cannot_be_bypassed_by_tcpm",
    "test_soak_audit.SoakAuditTests."
    "test_active_state_without_charging_indicator_fails",
    "test_soak_audit.SoakAuditTests."
    "test_source_tcpm_and_mp_contract_values_are_exact_per_sample",
}
EXCLUDED_NAMES = {
    "SHA256SUMS",
    "SHA256SUMS.verify.txt",
}
CANONICAL_TEST_REPORTS = {
    WINDOWS_RESULTS.name,
    LINUX_RESULTS.name,
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _is_package_file(path: Path) -> bool:
    relative = path.relative_to(TRIAL)
    name = relative.name
    if "__pycache__" in relative.parts or name in EXCLUDED_NAMES:
        return False
    if path.suffix in {".pyc", ".pyo"}:
        return False
    if name.startswith("test-run-"):
        return False
    if name.startswith("test-results") and name not in CANONICAL_TEST_REPORTS:
        return False
    return True


def package_files() -> list[Path]:
    return [
        path
        for path in sorted(TRIAL.rglob("*"))
        if path.is_file() and _is_package_file(path)
    ]


def _validate_manifest() -> dict:
    manifest = json.loads(MANIFEST.read_text())
    if manifest.get("trial_id") != "charging-integration-r15-fixed5v1500-20261027":
        raise SystemExit("unexpected trial id")
    if manifest.get("high_voltage_permitted") is not False:
        raise SystemExit("high voltage must remain disabled")
    profile = manifest.get("postboot", {})
    expected_profile = {
        "tcpm_current_ua": 1_500_000,
        "mp2650_input_current_ua": 900_000,
        "mp2650_charge_current_ua": 500_000,
        "voltage_uv": 5_000_000,
        "sink_pdos": "04019096",
    }
    for key, value in expected_profile.items():
        if profile.get(key) != value:
            raise SystemExit(f"unexpected postboot profile {key}: {profile.get(key)}")

    for target, row in manifest["device_files"].items():
        source = TRIAL / row["source"]
        if not source.is_file() or sha256(source) != row["sha256"]:
            raise SystemExit(f"device file hash mismatch: {target}")
    for row in [
        manifest["kernel_module"],
        *manifest.get("auxiliary_kernel_modules", []),
    ]:
        source = TRIAL / row["source"]
        if not source.is_file() or sha256(source) != row["new_sha256"]:
            raise SystemExit(f"module hash mismatch: {row['name']}")

    expected_snapshot = {
        path.relative_to(TRIAL).as_posix(): sha256(path)
        for path in sorted((TRIAL / "source-snapshot").rglob("*"))
        if path.is_file()
    }
    if manifest.get("source_snapshot") != expected_snapshot:
        raise SystemExit("source snapshot hashes do not match manifest")

    for name in ("boot", "logdump"):
        row = manifest["carriers"][name]
        path = Path(row["new_path"])
        if not path.is_file() or sha256(path) != row["new"]:
            raise SystemExit(f"new carrier hash mismatch: {name}")

    boot_receipt = Path(manifest["boot_receipt"]["path"])
    fat_receipt = Path(manifest["image"]["fat_receipt_path"])
    for label, path, expected in (
        ("boot receipt", boot_receipt, manifest["boot_receipt"]["sha256"]),
        ("FAT receipt", fat_receipt, manifest["image"]["fat_receipt_sha256"]),
        (
            "runtime DTB receipt",
            Path(manifest["runtime_dtb"]["fat_receipt_path"]),
            manifest["runtime_dtb"]["fat_receipt_sha256"],
        ),
    ):
        if not path.is_file() or sha256(path) != expected:
            raise SystemExit(f"{label} hash mismatch")
    return manifest


def _validate_operator_pin(manifest_hash: str) -> None:
    text = OPERATOR.read_text()
    pattern = re.compile(
        r"\$script:ExpectedProductionManifestSha256\s*=\s*'([0-9a-f]{64})'"
    )
    matches = pattern.findall(text)
    if matches != [manifest_hash]:
        raise SystemExit("operator canonical manifest pin is stale")
    if "__PRODUCTION_" in text:
        raise SystemExit("unresolved production pin placeholder")


def _validate_tests() -> tuple[dict, dict]:
    windows = json.loads(WINDOWS_RESULTS.read_text())
    linux = json.loads(LINUX_RESULTS.read_text())
    for label, report in (("Windows", windows), ("Linux", linux)):
        if not report.get("passed"):
            raise SystemExit(f"{label} tests are not passing")
        if report.get("failures") or report.get("errors"):
            raise SystemExit(f"{label} tests contain failures/errors")
        if report.get("ran") != EXPECTED_TEST_COUNT:
            raise SystemExit(
                f"unexpected {label} test count: {report.get('ran')}"
            )
        statuses = {
            row["test"]: row["status"]
            for row in report.get("tests", [])
            if isinstance(row, dict) and "test" in row
        }
        required = set(REQUIRED_PASSING_TESTS)
        if label == "Windows":
            # The physical-source cap regression compiles a C harness and is
            # intentionally skipped on hosts without gcc; Linux proves it.
            required.discard(
                "test_source_budget.SourceBudgetTests."
                "test_physical_source_cap_cannot_be_bypassed_by_tcpm"
            )
        missing = sorted(
            test for test in required if statuses.get(test) != "passed"
        )
        if missing:
            raise SystemExit(
                f"{label} is missing passing regression tests: {missing}"
            )

    newest_source = max(
        path.stat().st_mtime
        for path in package_files()
        if path.name not in CANONICAL_TEST_REPORTS
        and path.name not in {"package-result.json", "TRIAL-R15-PREPARATION.json"}
    )
    for label, report in (("Windows", windows), ("Linux", linux)):
        finished = float(report["started_unix"]) + float(report["duration_seconds"])
        if finished + 1 < newest_source:
            raise SystemExit(f"{label} tests predate current source changes")
    return windows, linux


def _write_metadata(manifest: dict, windows: dict, linux: dict) -> None:
    manifest_hash = sha256(MANIFEST)
    preparation = {
        "schema": "samurai-trial-r15-preparation-v2",
        "scope": (
            "offline fixed-5V 1.5A, 900mA input / 500mA charge, strict "
            "physical-source cap package freeze after dual-platform clean tests; "
            "no phone, SSH, adb, fastboot, reboot, or charging-hardware access"
        ),
        "trial_id": manifest["trial_id"],
        "manifest_sha256": manifest_hash,
        "image": manifest["image"],
        "kernel_version": manifest["kernel_version"],
        "profile": {
            "voltage_uv": manifest["postboot"]["voltage_uv"],
            "sink_pdo": manifest["postboot"]["sink_pdos"],
            "tcpm_current_ua": manifest["postboot"]["tcpm_current_ua"],
            "mp2650_input_current_ua": manifest["postboot"][
                "mp2650_input_current_ua"
            ],
            "mp2650_charge_current_ua": manifest["postboot"][
                "mp2650_charge_current_ua"
            ],
        },
        "carriers": manifest["carriers"],
        "boot_receipt": manifest["boot_receipt"],
        "runtime_dtb": manifest["runtime_dtb"],
        "kernel_module": manifest["kernel_module"],
        "auxiliary_kernel_modules": manifest["auxiliary_kernel_modules"],
        "rollback_baseline": manifest["rollback_baseline"],
        "high_voltage_permitted": False,
        "device_io_performed": False,
        "stage_preflight_pending": True,
        "runtime_acceptance_pending": True,
        "required_followup": [
            "stage preflight",
            "logdump then boot flash",
            "guard acceptance",
            "TCPM 1.5A and MP2650 900mA input / 500mA charge live proof",
            "screen-off non-suspend charging",
            "repeated Full/recharge",
            "suspend/resume",
            "physical USB remove/insert/cycle",
            "final clean soak",
        ],
    }
    (TRIAL / "TRIAL-R15-PREPARATION.json").write_bytes(
        (json.dumps(preparation, indent=2, sort_keys=True) + "\n").encode()
    )

    package = {
        "schema": "samurai-trial-r15-package-result-v2",
        "trial_id": manifest["trial_id"],
        "scope": (
            "offline fixed-5V 1.5A, 900mA input / 500mA charge, strict "
            "physical-source cap materialization; final Windows and Linux tests "
            "passed; no phone, SSH, fastboot, or charging hardware access"
        ),
        "manifest": str(MANIFEST),
        "manifest_sha256": manifest_hash,
        "device_root": manifest["device_root"],
        "kernel_release": manifest["release"],
        "kernel_version": manifest["kernel_version"],
        "image": {
            "path": manifest["image"]["path"],
            "bytes": manifest["image"]["bytes"],
            "sha256": manifest["image"]["sha256"],
            "fat_receipt_path": manifest["image"]["fat_receipt_path"],
            "fat_receipt_sha256": manifest["image"]["fat_receipt_sha256"],
        },
        "carriers": {
            name: {
                "new_path": row["new_path"],
                "bytes": row["bytes"],
                "sha256": row["new"],
                "rollback_path": row["old_path"],
                "rollback_sha256": row["old"],
            }
            for name, row in manifest["carriers"].items()
        },
        "boot_receipt": manifest["boot_receipt"],
        "runtime_dtb": {
            "path": manifest["runtime_dtb"]["path"],
            "bytes": manifest["runtime_dtb"]["bytes"],
            "sha256": manifest["runtime_dtb"]["sha256"],
            "fat_receipt_path": manifest["runtime_dtb"]["fat_receipt_path"],
            "fat_receipt_sha256": manifest["runtime_dtb"]["fat_receipt_sha256"],
        },
        "kernel_module": manifest["kernel_module"],
        "auxiliary_kernel_modules": manifest["auxiliary_kernel_modules"],
        "profile": preparation["profile"],
        "fixed_5v_only": True,
        "high_voltage_permitted": False,
        "tests": {
            "windows": {
                "ran": windows["ran"],
                "skipped": windows["skipped"],
                "failures": windows["failures"],
                "errors": windows["errors"],
                "sha256": sha256(WINDOWS_RESULTS),
            },
            "linux": {
                "ran": linux["ran"],
                "skipped": linux["skipped"],
                "failures": linux["failures"],
                "errors": linux["errors"],
                "sha256": sha256(LINUX_RESULTS),
            },
        },
        "package_state": "frozen_after_dual_platform_tests; stage_preflight_pending",
        "stage_preflight_pending": True,
        "runtime_acceptance_pending": True,
        "phone_or_fastboot_accessed": False,
    }
    (TRIAL / "package-result.json").write_text(
        json.dumps(package, indent=2, sort_keys=True) + "\n",
        newline="\n",
    )


def _freeze_and_verify() -> dict:
    files = package_files()
    sums = [
        f"{sha256(path)}  {path.relative_to(TRIAL).as_posix()}"
        for path in files
    ]
    (TRIAL / "SHA256SUMS").write_bytes(("\n".join(sums) + "\n").encode())

    staging = MIRROR.with_name(f".{MIRROR.name}.tmp-{os.getpid()}")
    if MIRROR.exists() or staging.exists():
        raise SystemExit(f"refusing to overwrite frozen trial or staging: {MIRROR}")
    staging.mkdir(parents=True)
    for path in files + [TRIAL / "SHA256SUMS"]:
        destination = staging / path.relative_to(TRIAL)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)

    verify_lines = []
    for line in (staging / "SHA256SUMS").read_text().splitlines():
        expected, relative = line.split("  ", 1)
        if sha256(staging / relative) != expected:
            raise SystemExit(f"mirror hash mismatch: {relative}")
        verify_lines.append(f"{relative}: OK")
    (staging / "SHA256SUMS.verify.txt").write_bytes(
        ("\n".join(verify_lines) + "\n").encode()
    )
    staging.rename(MIRROR)

    upload = MIRROR.with_name(MIRROR.name + "-upload.tar")
    upload_staging = upload.with_name(f".{upload.name}.tmp-{os.getpid()}")
    if upload.exists() or upload_staging.exists():
        raise SystemExit(f"refusing to overwrite upload archive: {upload}")
    with tarfile.open(upload_staging, "x") as archive:
        for path in sorted(MIRROR.rglob("*")):
            if path.is_file():
                archive.add(
                    path,
                    arcname=(Path(MIRROR.name) / path.relative_to(MIRROR)).as_posix(),
                )
    expected_members = sum(1 for path in MIRROR.rglob("*") if path.is_file())
    with tarfile.open(upload_staging, "r") as archive:
        members = archive.getmembers()
        if len(members) != expected_members:
            raise SystemExit("upload archive member count mismatch")
        for member in members:
            relative = Path(member.name).relative_to(MIRROR.name)
            stream = archive.extractfile(member)
            if not member.isfile() or stream is None:
                raise SystemExit(f"unexpected upload archive member: {member.name}")
            if stream.read() != (MIRROR / relative).read_bytes():
                raise SystemExit(f"upload archive byte mismatch: {member.name}")
    upload_staging.rename(upload)
    return {
        "mirror": str(MIRROR),
        "upload": str(upload),
        "files": len(files),
        "sums": len(sums),
        "manifest_sha256": sha256(MANIFEST),
        "package_result_sha256": sha256(MIRROR / "package-result.json"),
        "sha256sums_sha256": sha256(MIRROR / "SHA256SUMS"),
        "upload_sha256": sha256(upload),
        "verified": True,
    }


def main() -> None:
    manifest = _validate_manifest()
    manifest_hash = sha256(MANIFEST)
    _validate_operator_pin(manifest_hash)
    windows, linux = _validate_tests()
    _write_metadata(manifest, windows, linux)
    print(json.dumps(_freeze_and_verify(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
