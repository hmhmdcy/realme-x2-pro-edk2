"""Explicitly issue the boot-bound acceptance token after a read-only audit.

This is intentionally separate from postboot_audit.py.  The audit never writes;
this helper requires --execute and a second boot-id confirmation.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from trial_common import (
    DEVICE_ROOT,
    MANIFEST_PATH,
    TOKEN,
    TRIAL_ID,
    TrialError,
    atomic_write,
    manifest_sha256,
    read_json,
    require_regular,
    sha256_file,
)


def _boot_id() -> str:
    return Path("/proc/sys/kernel/random/boot_id").read_text().strip()


def issue(
    report_path: Path,
    *,
    root: Path = DEVICE_ROOT,
    manifest_path: Path = MANIFEST_PATH,
    confirm_boot_id: str,
    boot_id_reader=_boot_id,
    require_root: bool = True,
) -> dict:
    if require_root and (not hasattr(os, "geteuid") or os.geteuid() != 0):
        raise TrialError("root is required")
    boot = boot_id_reader()
    if confirm_boot_id != boot:
        raise TrialError("boot-id confirmation does not match the current boot")
    require_regular(report_path, require_root=require_root)
    require_regular(manifest_path, require_root=require_root)
    manifest = read_json(manifest_path)
    if (
        manifest.get("schema") != 1
        or manifest.get("trial_id") != TRIAL_ID
        or manifest.get("token") != TOKEN
        or manifest.get("high_voltage_permitted") is not False
    ):
        raise TrialError("installed manifest is not the fixed-5V trial manifest")
    report = read_json(report_path)
    if report.get("schema") != 1 or report.get("trial_id") != TRIAL_ID:
        raise TrialError("unexpected audit report")
    if report.get("passed") is not True or report.get("read_only") is not True:
        raise TrialError("acceptance requires a passed read-only audit")
    if report.get("accepted_token_written") is not False:
        raise TrialError("audit report must state that it did not write a token")
    if report.get("boot_id") != boot:
        raise TrialError("audit report belongs to a different boot")
    digest = manifest_sha256(manifest_path)
    if report.get("manifest_sha256") != digest:
        raise TrialError("audit report was produced for another manifest")
    target = root / "accepted.json"
    if target.exists():
        raise TrialError("acceptance token already exists")
    value = {
        "schema": 1,
        "trial_id": TRIAL_ID,
        "token": TOKEN,
        "boot_id": boot,
        "manifest_sha256": digest,
        "audit_report_sha256": sha256_file(report_path),
        "audit_report": str(report_path),
    }
    atomic_write(target, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode())
    return value


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--confirm-boot-id", required=True)
    parser.add_argument("--root", type=Path, default=DEVICE_ROOT)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if not args.execute:
        print(json.dumps({"execute_required": True, "token_written": False}))
        return 4
    value = issue(
        args.report,
        root=args.root,
        manifest_path=args.manifest,
        confirm_boot_id=args.confirm_boot_id,
    )
    print(json.dumps(value, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
