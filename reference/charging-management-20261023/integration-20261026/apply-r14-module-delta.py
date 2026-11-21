#!/usr/bin/python3
"""Install the r14 module/trial_common delta without rewriting carriers."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import time
from pathlib import Path


INSTALLED_TRIAL_MANIFEST = Path("/usr/share/samurai-charging/trial-manifest.json")
INSTALLED_MAIN_MANIFEST = Path("/usr/share/samurai-charging/manifest.json")
DEVICE_ROOT = Path("/root/charging-management-20261023/trial-517-r9-status-precharge")
MODULE_TARGET = Path(
    "/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/"
    "samurai-charging/samurai-mp2650.ko"
)
TRIAL_COMMON_TARGET = Path("/usr/lib/samurai-charging/trial_common.py")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def atomic_write(path: Path, raw: bytes, mode: int = 0o644) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.r14-module-{os.getpid()}")
    fd = os.open(
        tmp,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        mode,
    )
    try:
        with os.fdopen(fd, "wb", closefd=True) as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(tmp, mode)
        tmp.replace(path)
        parent = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(parent)
        finally:
            os.close(parent)
    except BaseException:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass
        raise


def validate(
    package: Path,
    expected_trial_sha: str,
    expected_main_sha: str,
    expected_module_sha: str,
    expected_common_sha: str,
) -> tuple[dict, dict, dict, dict]:
    if os.geteuid() != 0:
        raise RuntimeError("root is required")

    package_manifest_path = package / "manifest.json"
    package_manifest = read_json(package_manifest_path)
    current_trial_sha = sha256(INSTALLED_TRIAL_MANIFEST)
    current_main_sha = sha256(INSTALLED_MAIN_MANIFEST)
    if current_trial_sha != expected_trial_sha:
        raise RuntimeError(f"unexpected installed trial manifest: {current_trial_sha}")
    if current_main_sha != expected_main_sha:
        raise RuntimeError(f"unexpected installed main manifest: {current_main_sha}")
    if sha256(MODULE_TARGET) != expected_module_sha:
        raise RuntimeError("unexpected installed MP2650 module")
    if sha256(TRIAL_COMMON_TARGET) != expected_common_sha:
        raise RuntimeError("unexpected installed trial_common")

    current_trial = read_json(INSTALLED_TRIAL_MANIFEST)
    current_main = read_json(INSTALLED_MAIN_MANIFEST)
    package_module = package_manifest["kernel_module"]
    module_source = package / package_module["source"]
    if (
        package_module["target"] != MODULE_TARGET.as_posix()
        or package_module["new_bytes"] != module_source.stat().st_size
        or package_module["new_sha256"] != sha256(module_source)
    ):
        raise RuntimeError("package module mismatch")

    common_target = TRIAL_COMMON_TARGET.as_posix()
    common_row = package_manifest["device_files"][common_target]
    common_source = package / common_row["source"]
    if common_row["sha256"] != sha256(common_source):
        raise RuntimeError("package trial_common mismatch")

    current_module = current_trial.get("kernel_module")
    if (
        not isinstance(current_module, dict)
        or current_module.get("target") != MODULE_TARGET.as_posix()
        or current_module.get("new_sha256") != expected_module_sha
        or current_module.get("name") != package_module["name"]
        or current_module.get("source") != package_module["source"]
    ):
        raise RuntimeError("installed trial module metadata is not the expected baseline")
    old_common = current_trial["device_files"][common_target]["sha256"]
    if old_common != expected_common_sha:
        raise RuntimeError("installed trial_common metadata does not match the file")

    module_entry = current_main["modules"][package_module["name"]]
    if (
        module_entry.get("target") != MODULE_TARGET.as_posix()
        or module_entry.get("sha256") != expected_module_sha
        or current_main["installed_files"].get(MODULE_TARGET.as_posix())
        != expected_module_sha
        or current_main["installed_files"].get(common_target) != expected_common_sha
    ):
        raise RuntimeError("main manifest does not match installed module/common files")

    state = {
        "package_manifest_sha256": sha256(package_manifest_path),
        "current_trial_sha256": current_trial_sha,
        "current_main_sha256": current_main_sha,
        "changes": [
            {
                "target": MODULE_TARGET.as_posix(),
                "old_sha256": expected_module_sha,
                "new_sha256": package_module["new_sha256"],
            },
            {
                "target": common_target,
                "old_sha256": expected_common_sha,
                "new_sha256": common_row["sha256"],
            },
        ],
    }
    return package_manifest, current_trial, current_main, state


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--expected-trial-sha", required=True)
    parser.add_argument("--expected-main-sha", required=True)
    parser.add_argument("--expected-module-sha", required=True)
    parser.add_argument("--expected-common-sha", required=True)
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    package_manifest, current_trial, current_main, state = validate(
        args.package,
        args.expected_trial_sha,
        args.expected_main_sha,
        args.expected_module_sha,
        args.expected_common_sha,
    )
    receipt = {
        "schema": 1,
        "mode": "module-common-delta",
        "carrier_write": False,
        "package": str(args.package),
        "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
        "started_epoch": time.time(),
        **state,
    }
    if not args.execute:
        print(json.dumps(receipt, indent=2, sort_keys=True))
        return 0

    evidence = args.evidence or DEVICE_ROOT / time.strftime(
        "module-delta-r14-%Y%m%d-%H%M%S"
    )
    evidence.mkdir(parents=True, mode=0o700, exist_ok=False)
    backup = evidence / "before"
    backup.mkdir(mode=0o700)
    for source in (
        INSTALLED_TRIAL_MANIFEST,
        INSTALLED_MAIN_MANIFEST,
        MODULE_TARGET,
        TRIAL_COMMON_TARGET,
    ):
        shutil.copy2(source, backup / source.name)

    package_module = package_manifest["kernel_module"]
    common_target = TRIAL_COMMON_TARGET.as_posix()
    common_row = package_manifest["device_files"][common_target]
    module_raw = (args.package / package_module["source"]).read_bytes()
    common_raw = (args.package / common_row["source"]).read_bytes()
    trial_raw = (args.package / "manifest.json").read_bytes()

    main_after = json.loads(json.dumps(current_main))
    main_after["modules"][package_module["name"]]["sha256"] = (
        package_module["new_sha256"]
    )
    main_after["installed_files"][MODULE_TARGET.as_posix()] = package_module[
        "new_sha256"
    ]
    main_after["installed_files"][common_target] = common_row["sha256"]
    main_raw = (
        json.dumps(main_after, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()

    atomic_write(MODULE_TARGET, module_raw, 0o644)
    atomic_write(TRIAL_COMMON_TARGET, common_raw, 0o644)
    atomic_write(INSTALLED_MAIN_MANIFEST, main_raw, 0o644)
    atomic_write(INSTALLED_TRIAL_MANIFEST, trial_raw, 0o644)

    receipt["completed_epoch"] = time.time()
    receipt["installed"] = {
        MODULE_TARGET.as_posix(): sha256(MODULE_TARGET),
        common_target: sha256(TRIAL_COMMON_TARGET),
    }
    receipt["main_manifest_after_sha256"] = sha256(INSTALLED_MAIN_MANIFEST)
    receipt["trial_manifest_after_sha256"] = sha256(INSTALLED_TRIAL_MANIFEST)
    atomic_write(
        evidence / "result.json",
        (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode(),
        0o600,
    )
    os.sync()
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
