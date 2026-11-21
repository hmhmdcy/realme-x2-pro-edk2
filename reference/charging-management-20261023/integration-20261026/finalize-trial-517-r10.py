"""Finalize and mirror the #524 MP2650 hardening trial without device IO."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tarfile
from pathlib import Path


BASE = Path(__file__).resolve().parent
TRIAL = BASE / "trial-517-r9-status-precharge"
MIRROR = (
    Path(r"E:\edk2-samurai-out\charging-management-20261023")
    / "charging-integration-trial-20261027-r9-status-precharge-04"
)
MANIFEST = TRIAL / "manifest.json"
OPERATOR = TRIAL / "fastboot_operator.ps1"
EXCLUDED = {
    "SHA256SUMS",
    "SHA256SUMS.verify.txt",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def package_files() -> list[Path]:
    files = []
    for path in sorted(TRIAL.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(TRIAL)
        if "__pycache__" in relative.parts or relative.as_posix() in EXCLUDED:
            continue
        if relative.name.startswith("test-run-"):
            continue
        if path.suffix in {".pyc", ".pyo"}:
            continue
        files.append(path)
    return files


def main() -> None:
    if MIRROR.exists():
        raise SystemExit(f"refusing to overwrite frozen trial: {MIRROR}")
    manifest = json.loads(MANIFEST.read_text())
    if manifest.get("trial_id") != "charging-integration-r9-status-precharge-20261027":
        raise SystemExit("unexpected trial id")
    manifest_hash = sha256(MANIFEST)

    operator_text = OPERATOR.read_text()
    pattern = re.compile(
        r"(\$script:ExpectedProductionManifestSha256\s*=\s*')[0-9a-f]{64}(')"
    )
    updated, count = pattern.subn(rf"\g<1>{manifest_hash}\g<2>", operator_text)
    if count > 1:
        raise SystemExit("multiple canonical manifest pins in operator")
    if count == 1 and updated != operator_text:
        OPERATOR.write_text(updated, newline="\n")

    windows_results = TRIAL / "test-results-final-windows.json"
    linux_results = TRIAL / "test-results-final-linux.json"
    windows_tests = json.loads(windows_results.read_text())
    linux_tests = json.loads(linux_results.read_text())
    if not windows_tests.get("passed") or not linux_tests.get("passed"):
        raise SystemExit("test results are not both passing")
    if windows_tests.get("failures") or windows_tests.get("errors"):
        raise SystemExit("Windows test results contain failures")
    if linux_tests.get("failures") or linux_tests.get("errors"):
        raise SystemExit("Linux test results contain failures")

    manifest = json.loads(MANIFEST.read_text())
    preparation = {
        "schema": "samurai-trial-r10-preparation-v1",
        "scope": (
            "offline #524 r10 packaging and control-plane verification only; "
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
    (TRIAL / "TRIAL-R10-PREPARATION.json").write_bytes(
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
                "ran": windows_tests["ran"],
                "skipped": windows_tests["skipped"],
                "failures": windows_tests["failures"],
                "errors": windows_tests["errors"],
                "sha256": sha256(windows_results),
            },
            "linux": {
                "ran": linux_tests["ran"],
                "skipped": linux_tests["skipped"],
                "failures": linux_tests["failures"],
                "errors": linux_tests["errors"],
                "sha256": sha256(linux_results),
            },
        },
        "phone_or_fastboot_accessed": False,
        "runtime_acceptance_pending": True,
    }
    package_result = TRIAL / "package-result.json"
    package_result.write_text(
        json.dumps(package, indent=2, sort_keys=True) + "\n",
        newline="\n",
    )

    files = package_files()
    lines = []
    for path in files:
        relative = path.relative_to(TRIAL).as_posix()
        lines.append(f"{sha256(path)}  {relative}")
    (TRIAL / "SHA256SUMS").write_bytes(("\n".join(lines) + "\n").encode("utf-8"))

    staging = MIRROR.with_name(f".{MIRROR.name}.tmp-{os.getpid()}")
    if staging.exists():
        raise SystemExit(f"staging directory already exists: {staging}")
    staging.mkdir(parents=True)
    for path in files + [TRIAL / "SHA256SUMS"]:
        relative = path.relative_to(TRIAL)
        destination = staging / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)

    verify_lines = []
    for line in (staging / "SHA256SUMS").read_text().splitlines():
        expected, relative = line.split("  ", 1)
        actual = sha256(staging / relative)
        if actual != expected:
            raise SystemExit(f"mirror hash mismatch: {relative}")
        verify_lines.append(f"{relative}: OK")
    (staging / "SHA256SUMS.verify.txt").write_bytes(
        ("\n".join(verify_lines) + "\n").encode("utf-8")
    )
    staging.rename(MIRROR)

    upload = MIRROR.with_name(MIRROR.name + "-upload.tar")
    if upload.exists():
        raise SystemExit(f"refusing to overwrite upload archive: {upload}")
    with tarfile.open(upload, "x") as archive:
        for path in sorted(MIRROR.rglob("*")):
            if path.is_file():
                archive.add(
                    path,
                    arcname=(Path(MIRROR.name) / path.relative_to(MIRROR)).as_posix(),
                )
    print(
        json.dumps(
            {
                "mirror": str(MIRROR),
                "upload": str(upload),
                "files": len(files),
                "manifest_sha256": manifest_hash,
                "package_result_sha256": sha256(MIRROR / "package-result.json"),
                "verified": True,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
