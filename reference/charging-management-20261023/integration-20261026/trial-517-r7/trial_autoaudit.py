#!/usr/bin/env python3
"""Device-local polling audit and automatic boot-bound acceptance.

The OpenRC service starts managed charging first and launches this helper from
start_post.  A failed or incomplete audit only produces diagnostic evidence;
auto-acceptance.json and accepted.json are written only after a complete
read-only audit report passes for the current boot and installed manifest.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
import traceback
from pathlib import Path

import postboot_audit
from trial_common import (
    ACCEPTED_NAME,
    AUTO_ACCEPTANCE_NAME,
    AUTO_AUDIT_LAST_NAME,
    AUTO_AUDIT_REPORT_NAME,
    DEVICE_ROOT,
    MANIFEST_PATH,
    TOKEN,
    TRIAL_ID,
    WATCH_SECONDS,
    TrialError,
    atomic_write,
    canonical_json_bytes,
    manifest_sha256,
    read_json,
    require_regular,
    sha256_file,
    validate_complete_passed_audit_report,
)


def _boot_id() -> str:
    return Path("/proc/sys/kernel/random/boot_id").read_text().strip()


def _boottime() -> float:
    if hasattr(time, "CLOCK_BOOTTIME"):
        return time.clock_gettime(time.CLOCK_BOOTTIME)
    return time.monotonic()


def _manifest_value(manifest_path: Path, *, require_root: bool) -> tuple[dict, str]:
    require_regular(manifest_path, require_root=require_root)
    manifest = read_json(manifest_path)
    if (
        manifest.get("schema") != 1
        or manifest.get("trial_id") != TRIAL_ID
        or manifest.get("token") != TOKEN
        or manifest.get("high_voltage_permitted") is not False
    ):
        raise TrialError("installed manifest is not the fixed-5V trial manifest")
    return manifest, manifest_sha256(manifest_path)


def _valid_existing_acceptance(
    root: Path,
    *,
    manifest_path: Path,
    boot_id: str,
    manifest_digest: str,
    require_root: bool,
) -> dict | None:
    accepted_path = root / ACCEPTED_NAME
    if not accepted_path.exists():
        return None
    require_regular(accepted_path, require_root=require_root)
    value = read_json(accepted_path)
    if (
        value.get("schema") != 1
        or value.get("trial_id") != TRIAL_ID
        or value.get("token") != TOKEN
    ):
        raise TrialError("existing acceptance token is invalid")
    if value.get("boot_id") != boot_id:
        # Acceptance is intentionally boot-scoped.  A token from an earlier
        # boot is stale, not evidence for this boot, and must be replaceable
        # by a fresh read-only audit.
        return None
    if value.get("manifest_sha256") != manifest_digest:
        raise TrialError("existing acceptance token manifest mismatch")
    report_path = root / AUTO_AUDIT_REPORT_NAME
    require_regular(report_path, require_root=require_root)
    digest = sha256_file(report_path)
    if value.get("audit_report_sha256") != digest:
        raise TrialError("existing acceptance token report hash mismatch")
    report = read_json(report_path)
    if canonical_json_bytes(report) != report_path.read_bytes():
        raise TrialError("existing audit report is not canonical")
    validate_complete_passed_audit_report(
        report,
        boot_id=boot_id,
        manifest_sha256_value=manifest_digest,
    )
    auto_path = root / AUTO_ACCEPTANCE_NAME
    require_regular(auto_path, require_root=require_root)
    auto = read_json(auto_path)
    if (
        value.get("auto_acceptance_sha256") != sha256_file(auto_path)
        or auto.get("audit_report_sha256") != digest
        or auto.get("boot_id") != boot_id
        or auto.get("manifest_sha256") != manifest_digest
    ):
        raise TrialError("existing automatic acceptance evidence mismatch")
    return value


def record_acceptance(
    report: dict,
    *,
    root: Path = DEVICE_ROOT,
    manifest_path: Path = MANIFEST_PATH,
    boot_id_reader=_boot_id,
    require_root: bool = True,
) -> dict:
    """Atomically persist one complete passed report and its acceptance token."""
    root = Path(root)
    if require_root and (not hasattr(os, "geteuid") or os.geteuid() != 0):
        raise TrialError("root is required")
    if not root.is_dir():
        raise TrialError(f"private trial directory is missing: {root}")
    boot_id = boot_id_reader()
    _manifest, manifest_digest = _manifest_value(
        Path(manifest_path), require_root=require_root
    )
    validate_complete_passed_audit_report(
        report,
        boot_id=boot_id,
        manifest_sha256_value=manifest_digest,
    )
    existing = _valid_existing_acceptance(
        root,
        manifest_path=Path(manifest_path),
        boot_id=boot_id,
        manifest_digest=manifest_digest,
        require_root=require_root,
    )
    if existing is not None:
        return existing

    raw = canonical_json_bytes(report)
    report_digest = sha256_file_bytes(raw)
    report_path = root / AUTO_AUDIT_REPORT_NAME
    atomic_write(report_path, raw)

    auto_value = {
        "schema": 1,
        "trial_id": TRIAL_ID,
        "token": TOKEN,
        "boot_id": boot_id,
        "manifest_sha256": manifest_digest,
        "audit_report_sha256": report_digest,
        "audit_report": str(report_path),
        "report": report,
    }
    auto_raw = canonical_json_bytes(auto_value)
    auto_path = root / AUTO_ACCEPTANCE_NAME
    atomic_write(auto_path, auto_raw)
    accepted_value = {
        "schema": 1,
        "trial_id": TRIAL_ID,
        "token": TOKEN,
        "boot_id": boot_id,
        "manifest_sha256": manifest_digest,
        "audit_report_sha256": report_digest,
        "audit_report": str(report_path),
        "auto_acceptance": str(auto_path),
        "auto_acceptance_sha256": sha256_file_bytes(auto_raw),
    }
    accepted_path = root / ACCEPTED_NAME
    atomic_write(accepted_path, canonical_json_bytes(accepted_value))
    return accepted_value


def sha256_file_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _failure_report(attempt: int, error: BaseException) -> dict:
    return {
        "schema": 1,
        "trial_id": TRIAL_ID,
        "passed": False,
        "read_only": True,
        "accepted_token_written": False,
        "high_voltage_accessed": False,
        "attempt": attempt,
        "error": repr(error),
        "traceback": traceback.format_exc(),
    }


def _write_last_report(root: Path, value: dict) -> None:
    atomic_write(root / AUTO_AUDIT_LAST_NAME, canonical_json_bytes(value))


def _deadline_from_state(root: Path, boot_id: str, now: float) -> float:
    state_path = root / "state.json"
    if not state_path.exists():
        return now + WATCH_SECONDS
    state = read_json(state_path)
    if state.get("boot_id") != boot_id:
        raise TrialError("guard state belongs to a different boot")
    deadline = state.get("deadline_boottime")
    if type(deadline) not in (int, float):
        raise TrialError("guard watchdog deadline is missing")
    return float(deadline)


def run_until_accepted(
    *,
    root: Path = DEVICE_ROOT,
    manifest_path: Path = MANIFEST_PATH,
    interval: float = 5.0,
    deadline_boottime: float | None = None,
    max_attempts: int | None = None,
    boot_id_reader=_boot_id,
    boottime_reader=_boottime,
    sleeper=time.sleep,
    audit_fn=None,
    runtime_factory=None,
    require_root: bool = True,
) -> dict:
    """Poll the read-only audit and accept at most once inside this boot window."""
    root = Path(root)
    manifest_path = Path(manifest_path)
    boot_id = boot_id_reader()
    _manifest_value(manifest_path, require_root=require_root)
    manifest_digest = manifest_sha256(manifest_path)
    existing = _valid_existing_acceptance(
        root,
        manifest_path=manifest_path,
        boot_id=boot_id,
        manifest_digest=manifest_digest,
        require_root=require_root,
    )
    if existing is not None:
        return {"accepted": True, "attempts": 0, "token": existing}

    now = boottime_reader()
    deadline = (
        float(deadline_boottime)
        if deadline_boottime is not None
        else _deadline_from_state(root, boot_id, now)
    )
    if audit_fn is None:
        audit_fn = postboot_audit.audit
    if runtime_factory is None:
        runtime_factory = lambda: postboot_audit.AuditRuntime(
            root=root,
            manifest_path=manifest_path,
            require_symlinks=True,
        )
    attempts = 0
    while max_attempts is None or attempts < max_attempts:
        now = boottime_reader()
        if now >= deadline:
            return {
                "accepted": False,
                "attempts": attempts,
                "error": "watchdog deadline reached before a complete passed report",
            }
        attempts += 1
        try:
            report = audit_fn(runtime_factory())
        except BaseException as error:
            _write_last_report(root, _failure_report(attempts, error))
        else:
            if isinstance(report, dict) and report.get("passed") is True:
                try:
                    token = record_acceptance(
                        report,
                        root=root,
                        manifest_path=manifest_path,
                        boot_id_reader=boot_id_reader,
                        require_root=require_root,
                    )
                except BaseException as error:
                    _write_last_report(root, _failure_report(attempts, error))
                else:
                    return {
                        "accepted": True,
                        "attempts": attempts,
                        "token": token,
                    }
            else:
                _write_last_report(root, report)
        now = boottime_reader()
        if now >= deadline:
            break
        sleeper(min(max(interval, 0.01), deadline - now))
    return {
        "accepted": False,
        "attempts": attempts,
        "error": "watchdog deadline reached before a complete passed report",
    }


def _daemonize(root: Path) -> None:
    if not hasattr(os, "fork"):
        raise TrialError("daemon mode requires POSIX fork")
    first = os.fork()
    if first:
        raise SystemExit(0)
    os.setsid()
    second = os.fork()
    if second:
        os._exit(0)
    os.umask(0o077)
    os.chdir(root)
    log_path = root / "trial-autoaudit.log"
    log_fd = os.open(log_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    null_fd = os.open(os.devnull, os.O_RDONLY)
    os.dup2(null_fd, 0)
    os.dup2(log_fd, 1)
    os.dup2(log_fd, 2)
    os.close(null_fd)
    os.close(log_fd)


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEVICE_ROOT)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--interval", type=float, default=5.0)
    parser.add_argument("--deadline-boottime", type=float)
    parser.add_argument("--max-attempts", type=int)
    parser.add_argument("--daemon", action="store_true")
    args = parser.parse_args(argv)
    if args.daemon:
        _daemonize(args.root)
    result = run_until_accepted(
        root=args.root,
        manifest_path=args.manifest,
        interval=args.interval,
        deadline_boottime=args.deadline_boottime,
        max_attempts=args.max_attempts,
    )
    print(json.dumps(result, sort_keys=True))
    return 0 if result["accepted"] else 3


if __name__ == "__main__":
    raise SystemExit(_main())
