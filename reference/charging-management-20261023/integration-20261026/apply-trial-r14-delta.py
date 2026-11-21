#!/usr/bin/python3
"""Apply the userspace-only r14 delta without rewriting either carrier."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import time
from pathlib import Path


INSTALLED_TRIAL_MANIFEST = Path("/usr/share/samurai-charging/trial-manifest.json")
INSTALLED_MAIN_MANIFEST = Path("/usr/share/samurai-charging/manifest.json")
DEVICE_ROOT = Path("/root/charging-management-20261023/trial-517-r9-status-precharge")


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
    tmp = path.with_name(f".{path.name}.r14-{os.getpid()}")
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


def module_rows(manifest: dict) -> list[dict]:
    rows = [manifest["kernel_module"]]
    rows.extend(manifest.get("auxiliary_kernel_modules", []))
    return rows


def validate(
    package: Path,
    expected_trial_sha: str,
    expected_main_sha: str,
    expected_postboot_sha: str,
) -> tuple[dict, dict, dict, dict]:
    if os.geteuid() != 0:
        raise RuntimeError("root is required")
    package_manifest_path = package / "manifest.json"
    package_manifest = read_json(package_manifest_path)
    package_manifest_sha = sha256(package_manifest_path)
    current_trial_sha = sha256(INSTALLED_TRIAL_MANIFEST)
    current_main_sha = sha256(INSTALLED_MAIN_MANIFEST)
    if current_trial_sha != expected_trial_sha:
        raise RuntimeError(
            f"unexpected installed trial manifest: {current_trial_sha}"
        )
    if current_main_sha != expected_main_sha:
        raise RuntimeError(f"unexpected installed main manifest: {current_main_sha}")
    current_trial = read_json(INSTALLED_TRIAL_MANIFEST)
    current_main = read_json(INSTALLED_MAIN_MANIFEST)

    postboot_target = "/usr/lib/samurai-charging/postboot_audit.py"
    if sha256(Path(postboot_target)) != expected_postboot_sha:
        raise RuntimeError("unexpected installed postboot audit")

    changes = []
    for target, row in sorted(package_manifest["device_files"].items()):
        installed = Path(target)
        old = current_trial["device_files"].get(target)
        if not isinstance(old, dict):
            raise RuntimeError(f"installed trial manifest lacks {target}")
        if sha256(installed) != old["sha256"]:
            raise RuntimeError(f"installed file differs from current manifest: {target}")
        if current_main.get("installed_files", {}).get(target) != old["sha256"]:
            raise RuntimeError(f"main manifest differs from installed file: {target}")
        source = package / row["source"]
        new_sha = sha256(source)
        if new_sha != row["sha256"]:
            raise RuntimeError(f"package source hash mismatch: {target}")
        if new_sha != old["sha256"]:
            changes.append(
                {
                    "target": target,
                    "old_sha256": old["sha256"],
                    "new_sha256": new_sha,
                }
            )
    if changes != [
        {
            "target": postboot_target,
            "old_sha256": expected_postboot_sha,
            "new_sha256": package_manifest["device_files"][postboot_target]["sha256"],
        }
    ]:
        raise RuntimeError(f"unexpected userspace delta: {changes}")

    modules = current_main.get("modules")
    installed = current_main.get("installed_files")
    if not isinstance(modules, dict) or not isinstance(installed, dict):
        raise RuntimeError("main manifest module metadata missing")
    for row in module_rows(package_manifest):
        target = row["target"]
        source = package / row["source"]
        if source.stat().st_size != row["new_bytes"] or sha256(source) != row["new_sha256"]:
            raise RuntimeError(f"package module mismatch: {row['name']}")
        value = modules.get(row["name"])
        if (
            not isinstance(value, dict)
            or value.get("target") != target
            or value.get("sha256") != row["new_sha256"]
            or installed.get(target) != row["new_sha256"]
            or Path(target).stat().st_size != row["new_bytes"]
            or sha256(Path(target)) != row["new_sha256"]
        ):
            raise RuntimeError(f"installed module mismatch: {row['name']}")
    return package_manifest, current_trial, current_main, {
        "package_manifest_sha256": package_manifest_sha,
        "current_trial_sha256": current_trial_sha,
        "current_main_sha256": current_main_sha,
        "changes": changes,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--expected-trial-sha", required=True)
    parser.add_argument("--expected-main-sha", required=True)
    parser.add_argument("--expected-postboot-sha", required=True)
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    package_manifest, current_trial, current_main, state = validate(
        args.package,
        args.expected_trial_sha,
        args.expected_main_sha,
        args.expected_postboot_sha,
    )
    receipt = {
        "schema": 1,
        "mode": "userspace-delta",
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
        "delta-r14-07-%Y%m%d-%H%M%S"
    )
    evidence.mkdir(parents=True, mode=0o700, exist_ok=False)
    backup = evidence / "before"
    backup.mkdir(mode=0o700)
    for source in (
        INSTALLED_TRIAL_MANIFEST,
        INSTALLED_MAIN_MANIFEST,
        Path("/usr/lib/samurai-charging/postboot_audit.py"),
        DEVICE_ROOT / "state.json",
        DEVICE_ROOT / "accepted.json",
        DEVICE_ROOT / "auto-audit-report.json",
        DEVICE_ROOT / "auto-acceptance.json",
    ):
        if source.is_file():
            shutil.copy2(source, backup / source.name)

    main_after = json.loads(json.dumps(current_main))
    postboot_row = package_manifest["device_files"][
        "/usr/lib/samurai-charging/postboot_audit.py"
    ]
    main_after["installed_files"][postboot_row["target"]] = postboot_row["sha256"]
    main_raw = (
        json.dumps(main_after, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()
    postboot_raw = (args.package / postboot_row["source"]).read_bytes()
    trial_raw = (args.package / "manifest.json").read_bytes()

    try:
        atomic_write(Path(postboot_row["target"]), postboot_raw, 0o644)
        atomic_write(INSTALLED_MAIN_MANIFEST, main_raw, 0o644)
        atomic_write(INSTALLED_TRIAL_MANIFEST, trial_raw, 0o644)
    except BaseException:
        for source in backup.iterdir():
            if source.name == "state.json" and source.is_file():
                atomic_write(DEVICE_ROOT / source.name, source.read_bytes(), 0o600)
            elif source.name == "accepted.json" and source.is_file():
                atomic_write(DEVICE_ROOT / source.name, source.read_bytes(), 0o600)
            elif source.name.startswith(("auto-audit", "auto-acceptance")) and source.is_file():
                atomic_write(DEVICE_ROOT / source.name, source.read_bytes(), 0o600)
            elif source.name == "postboot_audit.py" and source.is_file():
                atomic_write(Path(postboot_row["target"]), source.read_bytes(), 0o644)
            elif source.name == "manifest.json" and source.is_file():
                atomic_write(INSTALLED_MAIN_MANIFEST, source.read_bytes(), 0o644)
            elif source.name == "trial-manifest.json" and source.is_file():
                atomic_write(INSTALLED_TRIAL_MANIFEST, source.read_bytes(), 0o644)
        raise

    receipt["completed_epoch"] = time.time()
    receipt["installed"] = {
        postboot_row["target"]: sha256(Path(postboot_row["target"])),
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
