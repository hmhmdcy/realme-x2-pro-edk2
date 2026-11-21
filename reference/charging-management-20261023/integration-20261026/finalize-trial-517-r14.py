"""Finalize and mirror the r14 userspace/audit fixes without device IO."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tarfile
import time
from pathlib import Path


BASE = Path(__file__).resolve().parent
TRIAL = BASE / "trial-517-r9-status-precharge"
OUT = Path(r"E:\edk2-samurai-out\charging-management-20261023")
MIRROR = OUT / "charging-integration-trial-20261027-r9-status-precharge-14"
MANIFEST = TRIAL / "manifest.json"
OPERATOR = TRIAL / "fastboot_operator.ps1"
WINDOWS_RESULTS = TRIAL / "test-results-final-windows.json"
LINUX_RESULTS = TRIAL / "test-results-final-linux.json"
EXPECTED_TEST_COUNT = 215
REQUIRED_PASSING_TESTS = {
    "test_trial_suite.PostbootAuditTests."
    "test_audit_accepts_full_hold_with_charger_disabled",
    "test_physical_cycle.PhysicalCycleTests."
    "test_full_hold_accepts_charger_disabled_status",
    "test_physical_wake.PhysicalWakeTests."
    "test_launcher_uploads_worker_common_dependency",
    "test_physical_wake.PhysicalWakeTests."
    "test_launcher_uses_wifi_control_for_both_wake_directions",
    "test_trial_suite.PostbootAuditTests."
    "test_audit_rejects_active_state_without_charging_indicator",
    "test_physical_cycle.PhysicalCycleTests."
    "test_gauge_charge_stop_prevents_healthy_recovery",
    "test_soak_audit.SoakAuditTests."
    "test_active_state_without_charging_indicator_fails",
    "test_soak_audit.SoakAuditTests."
    "test_full_hold_requires_full_battery_status",
    "test_physical_wake.PhysicalWakeTests."
    "test_dmesg_delta_survives_rolling_tail",
    "test_physical_cycle.PhysicalCycleTests."
    "test_launcher_leaves_evidence_creation_to_worker",
    "test_physical_cycle.PhysicalCycleTests."
    "test_worker_accepts_only_absent_or_empty_evidence_root",
    "test_mp2650_regressions.Mp2650RegressionTests."
    "test_timeout_boundary_and_auto_never_clear_cycle_timeout",
    "test_mp2650_regressions.Mp2650RegressionTests."
    "test_suspend_keeps_only_proven_active_charging",
}
CANONICAL_TEST_REPORTS = {
    WINDOWS_RESULTS.name,
    LINUX_RESULTS.name,
}
EXCLUDED_NAMES = {
    "SHA256SUMS",
    "SHA256SUMS.verify.txt",
    "TRIAL-R13-PREPARATION.json",
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
    if name.startswith(("test-run-", "test-results-r14-")):
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
    if manifest.get("trial_id") != "charging-integration-r9-status-precharge-20261027":
        raise SystemExit("unexpected trial id")
    for target, row in manifest["device_files"].items():
        source = TRIAL / row["source"]
        if not source.is_file() or sha256(source) != row["sha256"]:
            raise SystemExit(f"device file hash mismatch: {target}")
    expected_snapshot = {
        path.relative_to(TRIAL).as_posix(): sha256(path)
        for path in sorted((TRIAL / "source-snapshot").rglob("*"))
        if path.is_file()
    }
    if manifest.get("source_snapshot") != expected_snapshot:
        raise SystemExit("source snapshot hashes do not match manifest")
    return manifest


def _update_operator_pins(manifest_hash: str, manifest: dict) -> None:
    text = OPERATOR.read_text()
    pins = {
        "ExpectedProductionManifestSha256": manifest_hash,
        "ExpectedProductionImageSha256": manifest["image"]["sha256"],
    }
    for name, value in pins.items():
        pattern = re.compile(rf"(\$script:{name}\s*=\s*')[^']*(')")
        text, count = pattern.subn(rf"\g<1>{value}\g<2>", text)
        if count != 1:
            raise SystemExit(f"expected one canonical {name}, found {count}")
    if "__PRODUCTION_" in text:
        raise SystemExit("unresolved production pin placeholder")
    OPERATOR.write_text(text, newline="\n")


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
        missing = sorted(
            test for test in REQUIRED_PASSING_TESTS if statuses.get(test) != "passed"
        )
        if missing:
            raise SystemExit(f"{label} is missing passing regression tests: {missing}")

    newest_source = max(
        path.stat().st_mtime
        for path in [
            *(
                TRIAL / row["source"]
                for row in json.loads(MANIFEST.read_text())["device_files"].values()
            ),
            TRIAL / "physical_cycle_worker.py",
            TRIAL / "physical_wake_worker.py",
            TRIAL / "Invoke-PhysicalUsbCycle.ps1",
            TRIAL / "Invoke-PhysicalUsbWake.ps1",
            TRIAL / "tests" / "test_physical_cycle.py",
            TRIAL / "tests" / "test_physical_wake.py",
            TRIAL / "tests" / "test_trial_suite.py",
        ]
    )
    for label, report in (("Windows", windows), ("Linux", linux)):
        finished = float(report["started_unix"]) + float(report["duration_seconds"])
        if finished + 1 < newest_source:
            raise SystemExit(f"{label} tests predate current source changes")
    return windows, linux


def _write_metadata(manifest: dict, windows: dict, linux: dict) -> None:
    preparation = {
        "schema": "samurai-trial-r14-preparation-v1",
        "scope": (
            "offline r14 full-hold status and physical-wake dependency fixes; "
            "no phone, SSH, adb, fastboot, reboot, or charging-hardware access"
        ),
        "trial_id": manifest["trial_id"],
        "manifest_sha256": sha256(MANIFEST),
        "image": manifest["image"],
        "kernel_version": manifest["kernel_version"],
        "carriers": manifest["carriers"],
        "boot_receipt": manifest["boot_receipt"],
        "runtime_dtb": manifest["runtime_dtb"],
        "kernel_module": manifest["kernel_module"],
        "auxiliary_kernel_modules": manifest["auxiliary_kernel_modules"],
        "bq27xxx_evidence": manifest["image_provenance"]["bq27xxx_export"],
        "rollback_baseline": manifest["rollback_baseline"],
        "high_voltage_permitted": False,
        "device_io_performed": False,
        "runtime_acceptance_pending": True,
    }
    (TRIAL / "TRIAL-R14-PREPARATION.json").write_bytes(
        (json.dumps(preparation, indent=2, sort_keys=True) + "\n").encode()
    )

    package = {
        "schema": 1,
        "trial_id": manifest["trial_id"],
        "manifest": str(MANIFEST),
        "manifest_sha256": sha256(MANIFEST),
        "device_root": manifest["device_root"],
        "image": manifest["image"]["sha256"],
        "boot": manifest["carriers"]["boot"]["new"],
        "logdump": manifest["carriers"]["logdump"]["new"],
        "runtime_dtb": manifest["runtime_dtb"]["sha256"],
        "eud_policy": {
            "eud_com_status": manifest["postboot"]["eud_status_path"],
            "eud_off_route_status": manifest["postboot"]["eud_off_route_status_path"],
            "driver_binding": manifest["postboot"]["eud_off_route_driver_binding"],
        },
        "kernel_module": manifest["kernel_module"]["new_sha256"],
        "auxiliary_modules": {
            row["name"]: row["new_sha256"]
            for row in manifest["auxiliary_kernel_modules"]
        },
        "bq27xxx_evidence": manifest["image_provenance"]["bq27xxx_export"],
        "boot_identity_unchanged": manifest["packaging"][
            "boot_identity_unchanged"
        ],
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
        "phone_or_fastboot_accessed": False,
        "runtime_acceptance_pending": True,
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
            if stream is None or stream.read() != (MIRROR / relative).read_bytes():
                raise SystemExit(f"upload archive byte mismatch: {member.name}")
    upload_staging.rename(upload)
    return {
        "mirror": str(MIRROR),
        "upload": str(upload),
        "files": len(files),
        "sums": len(sums),
        "manifest_sha256": sha256(MANIFEST),
        "package_result_sha256": sha256(MIRROR / "package-result.json"),
        "upload_sha256": sha256(upload),
        "verified": True,
    }


def main() -> None:
    manifest = _validate_manifest()
    _update_operator_pins(sha256(MANIFEST), manifest)
    windows, linux = _validate_tests()
    _write_metadata(manifest, windows, linux)
    print(json.dumps(_freeze_and_verify(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
