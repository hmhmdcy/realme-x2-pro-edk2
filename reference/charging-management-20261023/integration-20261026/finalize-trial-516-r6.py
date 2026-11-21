"""Finalize and mirror the #516 attempt-5 control package without device IO."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path


BASE = Path(__file__).resolve().parent
TRIAL = BASE / "trial-516-r6"
MIRROR = (
    Path(r"E:\edk2-samurai-out\charging-management-20261023")
    / "charging-integration-trial-20261026-10"
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
    manifest = json.loads(MANIFEST.read_text())
    if manifest.get("trial_id") != "charging-integration-516-20261026-10":
        raise SystemExit("unexpected trial id")
    manifest_hash = sha256(MANIFEST)

    operator_text = OPERATOR.read_text()
    pattern = re.compile(
        r"(\$script:ExpectedProductionManifestSha256\s*=\s*')[0-9a-f]{64}(')"
    )
    updated, count = pattern.subn(rf"\g<1>{manifest_hash}\g<2>", operator_text)
    if count != 1:
        raise SystemExit("expected exactly one canonical manifest hash")
    if updated != operator_text:
        OPERATOR.write_text(updated)

    windows_tests = json.loads((TRIAL / "test-results.json").read_text())
    linux_tests = json.loads((TRIAL / "test-results-linux.json").read_text())
    if not windows_tests.get("passed") or not linux_tests.get("passed"):
        raise SystemExit("test results are not both passing")
    if windows_tests.get("failures") or windows_tests.get("errors"):
        raise SystemExit("Windows test results contain failures")
    if linux_tests.get("failures") or linux_tests.get("errors"):
        raise SystemExit("Linux test results contain failures")

    manifest = json.loads(MANIFEST.read_text())
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
        "tests": {
            "windows": {
                "ran": windows_tests["ran"],
                "skipped": windows_tests["skipped"],
                "failures": windows_tests["failures"],
                "errors": windows_tests["errors"],
                "sha256": sha256(TRIAL / "test-results.json"),
            },
            "linux": {
                "ran": linux_tests["ran"],
                "skipped": linux_tests["skipped"],
                "failures": linux_tests["failures"],
                "errors": linux_tests["errors"],
                "sha256": sha256(TRIAL / "test-results-linux.json"),
            },
        },
        "phone_or_fastboot_accessed": False,
        "runtime_acceptance_pending": True,
    }
    package_result = TRIAL / "package-result.json"
    package_result.write_text(json.dumps(package, indent=2, sort_keys=True) + "\n")

    files = package_files()
    lines = []
    for path in files:
        relative = path.relative_to(TRIAL).as_posix()
        lines.append(f"{sha256(path)}  {relative}")
    (TRIAL / "SHA256SUMS").write_bytes(("\n".join(lines) + "\n").encode("utf-8"))

    MIRROR.mkdir(parents=True, exist_ok=True)
    for path in files + [TRIAL / "SHA256SUMS"]:
        relative = path.relative_to(TRIAL)
        destination = MIRROR / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)

    verify_lines = []
    for line in (MIRROR / "SHA256SUMS").read_text().splitlines():
        expected, relative = line.split("  ", 1)
        actual = sha256(MIRROR / relative)
        if actual != expected:
            raise SystemExit(f"mirror hash mismatch: {relative}")
        verify_lines.append(f"{relative}: OK")
    (MIRROR / "SHA256SUMS.verify.txt").write_bytes(
        ("\n".join(verify_lines) + "\n").encode("utf-8")
    )
    print(
        json.dumps(
            {
                "mirror": str(MIRROR),
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
