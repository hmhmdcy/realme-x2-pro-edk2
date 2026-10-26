"""Fail-closed userspace guard for the #513 charging trial.

The guard is called from the OpenRC wrapper's start_pre hook.  It starts one
300-second watchdog for the current boot.  If a boot-bound acceptance token is
not present when the deadline expires, it restores the old boot carrier, then
the old logdump carrier, then the original init service, and requests reboot.

The guard cannot recover a hang that happens before Linux userspace starts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import subprocess
import sys
import time
from pathlib import Path

try:
    import fcntl
except ImportError:  # local Windows control tests
    fcntl = None

from trial_common import (
    COMMON_PATH,
    DEVICE_ROOT,
    GUARD_PATH,
    MAIN_MANIFEST_PATH,
    MAIN_MANIFEST_SHA256,
    MANIFEST_PATH,
    OLD_CARRIER_SHA256,
    NEW_CARRIER_SHA256,
    PARTITION_BYTES,
    SERVICE_PATH,
    TOKEN,
    TRIAL_ID,
    VERSION,
    WATCH_SECONDS,
    TrialError,
    atomic_write,
    copy_verified,
    manifest_sha256,
    read_json,
    require_regular,
    sha256_file,
)


def _default_boot_id(proc_root: Path) -> str:
    return (proc_root / "sys/kernel/random/boot_id").read_text().strip()


def _default_version(proc_root: Path) -> str:
    return (proc_root / "version").read_text().strip()


def _default_boottime() -> float:
    return time.clock_gettime(time.CLOCK_BOOTTIME)


def _default_reboot() -> None:
    for candidate in ("/system/bin/reboot", "/sbin/reboot", "/usr/sbin/reboot"):
        if Path(candidate).exists():
            subprocess.run([candidate], check=True, timeout=20)
            return
    raise TrialError("reboot command not found")


def _is_root() -> bool:
    return hasattr(os, "geteuid") and os.geteuid() == 0


class Runtime:
    def __init__(
        self,
        *,
        root: Path = DEVICE_ROOT,
        proc_root: Path = Path("/proc"),
        sys_root: Path = Path("/sys"),
        dev_root: Path = Path("/dev"),
        target_root: Path = Path("/"),
        manifest_path: Path | None = None,
        devices: dict[str, Path] | None = None,
        identities: dict[str, dict] | None = None,
        require_root: bool = True,
        strict_carrier_pins: bool = True,
        partition_bytes: dict[str, int] | None = None,
        clock=time.monotonic,
        boottime=_default_boottime,
        sleep=time.sleep,
        reboot=None,
    ) -> None:
        self.root = Path(root)
        self.proc_root = Path(proc_root)
        self.sys_root = Path(sys_root)
        self.dev_root = Path(dev_root)
        self.target_root = Path(target_root)
        self.manifest_path = Path(manifest_path or self.target(MANIFEST_PATH))
        self.devices = {key: Path(value) for key, value in (devices or {}).items()}
        self.identities = identities or {}
        self.require_root = require_root
        self.strict_carrier_pins = strict_carrier_pins
        self.partition_bytes = dict(partition_bytes or PARTITION_BYTES)
        self.clock = clock
        self.boottime = boottime
        self.sleep = sleep
        self.reboot = reboot or _default_reboot

    def target(self, path: Path) -> Path:
        path = Path(path)
        if self.target_root == Path("/"):
            return path
        return self.target_root / path.relative_to("/")


def _check_runtime(rt: Runtime) -> None:
    if rt.require_root and not _is_root():
        raise TrialError("root is required")
    if not rt.root.is_dir():
        raise TrialError(f"private trial directory is missing: {rt.root}")


def load_manifest(rt: Runtime) -> dict:
    require_regular(rt.manifest_path, require_root=rt.require_root)
    manifest = read_json(rt.manifest_path)
    if manifest.get("schema") != 1:
        raise TrialError("unsupported manifest schema")
    if manifest.get("trial_id") != TRIAL_ID:
        raise TrialError("unexpected trial id")
    if manifest.get("kernel_version") != VERSION:
        raise TrialError("unexpected kernel version pin")
    if manifest.get("watch_seconds") != WATCH_SECONDS:
        raise TrialError("unexpected watch timeout")
    if manifest.get("token") != TOKEN:
        raise TrialError("unexpected acceptance token")
    if manifest.get("high_voltage_permitted") is not False:
        raise TrialError("manifest must keep high voltage disabled")
    files = manifest.get("device_files")
    if not isinstance(files, dict):
        raise TrialError("device_files missing")
    targets = {row.get("target") for row in files.values() if isinstance(row, dict)}
    required = {str(COMMON_PATH), str(GUARD_PATH), str(SERVICE_PATH)}
    if not required.issubset(targets):
        raise TrialError("guard/common/service install targets missing")
    for row in files.values():
        if not isinstance(row, dict):
            raise TrialError("invalid device file entry")
        if not isinstance(row.get("sha256"), str) or len(row["sha256"]) != 64:
            raise TrialError("invalid device file hash")
    main_manifest = manifest.get("main_manifest")
    if not isinstance(main_manifest, dict):
        raise TrialError("main_manifest metadata missing")
    if main_manifest.get("target") != str(MAIN_MANIFEST_PATH):
        raise TrialError("unexpected main manifest target")
    if main_manifest.get("service_target") != str(SERVICE_PATH):
        raise TrialError("unexpected main manifest service target")
    if (
        rt.strict_carrier_pins
        and main_manifest.get("old_sha256") != MAIN_MANIFEST_SHA256
    ):
        raise TrialError("unexpected main manifest pin")
    carriers = manifest.get("carriers")
    if not isinstance(carriers, dict) or set(carriers) != set(rt.partition_bytes):
        raise TrialError("carrier metadata missing")
    for name, size in rt.partition_bytes.items():
        row = carriers[name]
        if row.get("bytes") != size:
            raise TrialError(f"unexpected {name} size")
        if rt.strict_carrier_pins:
            if row.get("old") != OLD_CARRIER_SHA256[name]:
                raise TrialError(f"unexpected old {name} hash")
            if row.get("new") != NEW_CARRIER_SHA256[name]:
                raise TrialError(f"unexpected new {name} hash")
    return manifest


def verify_installed(rt: Runtime, manifest: dict) -> None:
    for row in manifest["device_files"].values():
        target = rt.target(Path(row["target"]))
        require_regular(target, require_root=rt.require_root)
        if sha256_file(target) != row["sha256"]:
            raise TrialError(f"installed file hash mismatch: {target}")
    main_target = rt.target(MAIN_MANIFEST_PATH)
    require_regular(main_target, require_root=rt.require_root, max_mode=0o644)
    main_value = read_json(main_target)
    installed = main_value.get("installed_files")
    if not isinstance(installed, dict):
        raise TrialError("main manifest installed_files missing")
    expected_service = manifest["device_files"][str(SERVICE_PATH)]["sha256"]
    if installed.get(str(SERVICE_PATH)) != expected_service:
        raise TrialError("main manifest does not pin the trial service")


def current_boot(rt: Runtime) -> str:
    return _default_boot_id(rt.proc_root)


def current_version(rt: Runtime, version_reader=None) -> str:
    if version_reader is not None:
        return version_reader()
    return _default_version(rt.proc_root)


def state_write(rt: Runtime, event: str, **values) -> None:
    payload = {
        "event": event,
        "boot_id": current_boot(rt),
        "boottime": rt.boottime(),
        **values,
    }
    atomic_write(
        rt.root / "state.json",
        (json.dumps(payload, sort_keys=True) + "\n").encode("utf-8"),
    )


def accepted_token(rt: Runtime, manifest: dict) -> bool:
    path = rt.root / "accepted.json"
    if not path.exists():
        return False
    try:
        require_regular(path, require_root=rt.require_root)
        value = read_json(path)
    except (OSError, TrialError, ValueError, json.JSONDecodeError):
        return False
    boot = current_boot(rt)
    return (
        value.get("schema") == 1
        and value.get("trial_id") == TRIAL_ID
        and value.get("token") == TOKEN
        and value.get("boot_id") == boot
        and value.get("manifest_sha256") == manifest_sha256(rt.manifest_path)
        and isinstance(value.get("audit_report_sha256"), str)
        and len(value["audit_report_sha256"]) == 64
    )


def _device_for(rt: Runtime, name: str) -> Path:
    if name in rt.devices:
        return rt.devices[name]
    return rt.dev_root / "disk/by-partlabel" / name


def partition_identity(rt: Runtime, name: str) -> dict:
    if name in rt.identities:
        return rt.identities[name]
    device = _device_for(rt, name).resolve(strict=True)
    block = rt.sys_root / "class/block" / device.name
    partuuids = []
    uuid_root = rt.dev_root / "disk/by-partuuid"
    if uuid_root.is_dir():
        for alias in uuid_root.iterdir():
            try:
                if alias.resolve(strict=True) == device:
                    partuuids.append(alias.name)
            except OSError:
                continue
    if len(partuuids) != 1:
        raise TrialError(f"expected one partuuid for {name}")
    return {
        "partuuid": partuuids[0],
        "start": int((block / "start").read_text().strip()),
        "sectors": int((block / "size").read_text().strip()),
        "partition": int((block / "partition").read_text().strip()),
    }


def _verify_partition_identity(rt: Runtime, stage: dict, name: str) -> None:
    expected = stage["partition_identity"][name]
    actual = partition_identity(rt, name)
    if actual != expected:
        raise TrialError(f"partition identity changed: {name}")
    device = _device_for(rt, name)
    if device.is_block_device():
        size = actual["sectors"] * 512
    elif device.is_file():
        size = device.stat().st_size
    else:
        raise TrialError(f"carrier device missing: {device}")
    if size != rt.partition_bytes[name]:
        raise TrialError(f"carrier size changed: {name}")


def _copy_carrier_to_backup(rt: Runtime, name: str, expected_sha256: str) -> Path:
    source = _device_for(rt, name)
    if not source.is_file() and not source.is_block_device():
        raise TrialError(f"carrier device missing: {source}")
    destination = rt.root / "old" / f"{name}.img"
    if destination.exists() or destination.is_symlink():
        raise TrialError(f"refusing to overwrite old carrier: {destination}")
    copy_verified(
        source,
        destination,
        expected_sha256=expected_sha256,
        expected_bytes=rt.partition_bytes[name],
    )
    return destination


def ensure_old_backups(rt: Runtime, manifest: dict, stage: dict) -> dict[str, Path]:
    result = {}
    for name, size in rt.partition_bytes.items():
        _verify_partition_identity(rt, stage, name)
        expected = manifest["carriers"][name]["old"]
        backup = rt.root / "old" / f"{name}.img"
        if backup.exists():
            info = require_regular(backup, require_root=rt.require_root)
            if info.st_size != size or sha256_file(backup) != expected:
                raise TrialError(f"old carrier backup is invalid: {name}")
        else:
            # This path is only safe while the current partition is still old.
            device = _device_for(rt, name)
            if sha256_file(device) != expected:
                raise TrialError(f"old carrier backup unavailable: {name}")
            _copy_carrier_to_backup(rt, name, expected)
        result[name] = backup
    return result


def _check_device_not_mounted(rt: Runtime, name: str, device: Path) -> None:
    mounts = rt.proc_root / "mounts"
    if not mounts.exists():
        return
    aliases = {str(device), str(rt.dev_root / "disk/by-partlabel" / name)}
    mounted = {line.split()[0] for line in mounts.read_text().splitlines() if line.strip()}
    if aliases & mounted:
        raise TrialError(f"refusing to write mounted carrier: {name}")


def write_carrier_from_backup(rt: Runtime, stage: dict, name: str, expected_sha256: str) -> None:
    _verify_partition_identity(rt, stage, name)
    device = _device_for(rt, name)
    _check_device_not_mounted(rt, name, device)
    source = rt.root / "old" / f"{name}.img"
    require_regular(source, require_root=rt.require_root)
    if source.stat().st_size != rt.partition_bytes[name]:
        raise TrialError(f"rollback image size mismatch: {name}")
    if sha256_file(source) != expected_sha256:
        raise TrialError(f"rollback image hash mismatch: {name}")
    if sha256_file(device) == expected_sha256:
        return
    flags = os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
    target_fd = os.open(device, flags)
    try:
        with os.fdopen(target_fd, "r+b", buffering=0) as target, source.open("rb") as stream:
            target.seek(0)
            remaining = rt.partition_bytes[name]
            while remaining:
                block = stream.read(min(1024 * 1024, remaining))
                if not block:
                    raise TrialError(f"short rollback image: {name}")
                view = memoryview(block)
                while view:
                    written = target.write(view)
                    if not written:
                        raise TrialError(f"short rollback write: {name}")
                    view = view[written:]
                remaining -= len(block)
            if device.is_file():
                target.truncate(rt.partition_bytes[name])
            os.fsync(target.fileno())
    except BaseException:
        raise
    if sha256_file(device) != expected_sha256:
        raise TrialError(f"rollback readback mismatch: {name}")


def restore_original_service(rt: Runtime, manifest: dict, stage: dict) -> None:
    main_backup = rt.root / "original/main-manifest.json"
    main_info = require_regular(main_backup, require_root=rt.require_root)
    original_main = stage["original_main_manifest"]
    if sha256_file(main_backup) != original_main["sha256"]:
        raise TrialError("original main manifest backup hash mismatch")
    original_main_value = read_json(main_backup)
    installed = original_main_value.get("installed_files")
    if not isinstance(installed, dict):
        raise TrialError("original main manifest installed_files missing")
    original_service_sha256 = stage["original_service"]["sha256"]
    service_target = manifest["main_manifest"]["service_target"]
    if installed.get(service_target) != original_service_sha256:
        raise TrialError("original main manifest service binding mismatch")
    main_target = rt.target(MAIN_MANIFEST_PATH)
    atomic_write(main_target, main_backup.read_bytes(), stat.S_IMODE(main_info.st_mode))
    if _is_root():
        os.chown(main_target, main_info.st_uid, main_info.st_gid)
    if sha256_file(main_target) != original_main["sha256"]:
        raise TrialError("original main manifest readback mismatch")

    backup = rt.root / "original/samurai-charging"
    info = require_regular(backup, require_root=rt.require_root)
    expected = stage["original_service"]["sha256"]
    if sha256_file(backup) != expected:
        raise TrialError("original service backup hash mismatch")
    target = rt.target(Path(stage["original_service"]["target"]))
    atomic_write(target, backup.read_bytes(), stat.S_IMODE(info.st_mode))
    if _is_root():
        os.chown(target, info.st_uid, info.st_gid)
    if sha256_file(target) != expected:
        raise TrialError("original service readback mismatch")
    # Remove only files that this trial installed.  The private evidence tree is
    # intentionally retained for post-incident inspection.
    for row in manifest["device_files"].values():
        path = rt.target(Path(row["target"]))
        if path == target:
            continue
        try:
            if path.is_file() and not path.is_symlink() and sha256_file(path) == row["sha256"]:
                path.unlink()
        except FileNotFoundError:
            continue
    try:
        trial_manifest = rt.manifest_path
        if trial_manifest.is_file() and not trial_manifest.is_symlink():
            trial_manifest.unlink()
    except FileNotFoundError:
        pass


def _sync() -> None:
    if hasattr(os, "sync"):
        os.sync()


def rollback(rt: Runtime, manifest: dict, stage: dict, reason: str, *, reboot: bool) -> dict:
    state_write(rt, "restoring", reason=reason)
    order = []
    # Old firmware first: never leave the old kernel paired with a new Type-C
    # DT/APSD carrier after a partial host write.
    for name in ("boot", "logdump"):
        write_carrier_from_backup(rt, stage, name, manifest["carriers"][name]["old"])
        order.append(name)
    restore_original_service(rt, manifest, stage)
    evidence = {
        "schema": 1,
        "trial_id": TRIAL_ID,
        "reason": reason,
        "boot_id": current_boot(rt),
        "boottime": rt.boottime(),
        "carrier_restore_order": order,
        "carriers_restored": {
            name: sha256_file(_device_for(rt, name)) for name in ("boot", "logdump")
        },
        "main_manifest_restored": True,
        "main_manifest_sha256": sha256_file(
            rt.target(MAIN_MANIFEST_PATH)
        ),
        "original_service_restored": True,
        "reboot_requested": bool(reboot),
    }
    atomic_write(
        rt.root / "rollback.json",
        (json.dumps(evidence, sort_keys=True) + "\n").encode("utf-8"),
    )
    state_write(rt, "restored", reason=reason, reboot_requested=bool(reboot))
    _sync()
    if reboot:
        rt.reboot()
    return evidence


def verify_new_pair(rt: Runtime, manifest: dict, stage: dict) -> dict:
    readback = {
        "schema": 1,
        "source": "guard",
        "boot_id": current_boot(rt),
        "partition_identity": {},
        "carriers": {},
    }
    for name in ("boot", "logdump"):
        _verify_partition_identity(rt, stage, name)
        actual = sha256_file(_device_for(rt, name))
        expected = manifest["carriers"][name]["new"]
        if actual != expected:
            raise TrialError(f"host carrier write is not the expected new {name}")
        readback["partition_identity"][name] = stage["partition_identity"][name]
        readback["carriers"][name] = {
            "path": str(_device_for(rt, name)),
            "sha256": actual,
            "expected": expected,
            "bytes": rt.partition_bytes[name],
        }
    return readback


def start_watch(rt: Runtime, deadline_boottime: float) -> None:
    if fcntl is None:
        raise TrialError("watchdog requires POSIX fcntl")
    lock_path = rt.root / "watchdog.lock"
    lock_fd = os.open(
        lock_path,
        os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    try:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        state_write(rt, "watchdog-starting", deadline_boottime=deadline_boottime)
        with (rt.root / "watchdog.stdout").open("ab") as stdout, (
            rt.root / "watchdog.stderr"
        ).open("ab") as stderr:
            child = subprocess.Popen(
                [
                    sys.executable,
                    "-B",
                    str(rt.target(GUARD_PATH)),
                    "watch",
                    "--deadline-boottime",
                    repr(deadline_boottime),
                    "--lock-fd",
                    str(lock_fd),
                ],
                stdin=subprocess.DEVNULL,
                stdout=stdout,
                stderr=stderr,
                start_new_session=True,
                close_fds=True,
                pass_fds=(lock_fd,),
            )
        state_write(
            rt,
            "watchdog-running",
            pid=child.pid,
            deadline_boottime=deadline_boottime,
        )
    finally:
        os.close(lock_fd)


def prestart(rt: Runtime, *, version_reader=None) -> None:
    _check_runtime(rt)
    manifest = load_manifest(rt)
    verify_installed(rt, manifest)
    stage = read_json(rt.root / "stage.json")
    if stage.get("trial_id") != TRIAL_ID:
        raise TrialError("stage receipt has the wrong trial id")
    boot = current_boot(rt)
    version = current_version(rt, version_reader)
    state_write(
        rt,
        "prestart",
        stage_boot_id=stage.get("boot_id"),
        kernel_version=version,
    )
    if boot == stage.get("boot_id"):
        # The wrapper was installed during the old boot.  Do not arm a watchdog
        # until the host has actually left that boot for the flashed pair.
        state_write(rt, "stage-pending-host-reboot", stage_boot_id=stage.get("boot_id"))
        return
    if VERSION not in version:
        rollback(rt, manifest, stage, "unexpected-kernel", reboot=True)
        return
    ensure_old_backups(rt, manifest, stage)
    readback = verify_new_pair(rt, manifest, stage)
    atomic_write(
        rt.root / "carrier-readback.json",
        (json.dumps(readback, sort_keys=True) + "\n").encode("utf-8"),
    )
    state_write(rt, "carrier-readback-verified", carrier_readback=readback)
    if accepted_token(rt, manifest):
        state_write(rt, "accepted")
        return
    deadline = rt.boottime() + WATCH_SECONDS
    start_watch(rt, deadline)


def watch(rt: Runtime, *, deadline_boottime: float, lock_fd: int | None = None) -> None:
    _check_runtime(rt)
    manifest = load_manifest(rt)
    verify_installed(rt, manifest)
    stage = read_json(rt.root / "stage.json")
    if lock_fd is not None and fcntl is not None:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            pass
    while True:
        if VERSION not in current_version(rt):
            rollback(rt, manifest, stage, "watchdog-kernel-changed", reboot=True)
            return
        if accepted_token(rt, manifest):
            state_write(rt, "accepted")
            return
        now = rt.boottime()
        if now >= deadline_boottime:
            rollback(
                rt,
                manifest,
                stage,
                "no-boot-bound-acceptance-within-300s",
                reboot=True,
            )
            return
        rt.sleep(min(1.0, max(0.01, deadline_boottime - now)))


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prestart", "watch", "check"))
    parser.add_argument("--deadline-boottime", type=float)
    parser.add_argument("--lock-fd", type=int)
    args = parser.parse_args(argv)
    os.umask(0o077)
    rt = Runtime()
    if args.action == "prestart":
        prestart(rt)
        return 0
    if args.action == "watch":
        if args.deadline_boottime is None:
            raise TrialError("watch requires --deadline-boottime")
        watch(rt, deadline_boottime=args.deadline_boottime, lock_fd=args.lock_fd)
        return 0
    manifest = load_manifest(rt)
    verify_installed(rt, manifest)
    print(
        json.dumps(
            {
                "passed": True,
                "trial_id": TRIAL_ID,
                "boot_id": current_boot(rt),
                "version": current_version(rt),
                "accepted": accepted_token(rt, manifest),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
