"""Install only the trial guard/service, back up old carriers, enter bootloader.

This helper never writes boot or logdump.  The host fastboot operator is solely
responsible for writing the new carriers after checking this stage receipt.
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import platform
import stat
import subprocess
import sys
from pathlib import Path

from trial_common import (
    COMMON_PATH,
    DEVICE_ROOT,
    GUARD_PATH,
    MANIFEST_PATH,
    OLD_CARRIER_SHA256,
    PARTITION_BYTES,
    SERVICE_PATH,
    TOKEN,
    TRIAL_ID,
    VERSION,
    WATCH_SECONDS,
    TrialError,
    atomic_write,
    copy_verified,
    read_json,
    require_regular,
    sha256_file,
)

try:
    import fcntl
except ImportError:  # local Windows control tests
    fcntl = None


def _is_root() -> bool:
    return hasattr(os, "geteuid") and os.geteuid() == 0


def _default_serial() -> str:
    for command in ("/system/bin/getprop", "/usr/bin/getprop"):
        if Path(command).exists():
            value = subprocess.run(
                [command, "ro.serialno"],
                check=True,
                capture_output=True,
                text=True,
                timeout=10,
            ).stdout.strip()
            if value:
                return value
    for path in (
        Path("/sys/class/android_usb/android0/iSerial"),
        Path("/proc/sys/kernel/random/boot_id"),
    ):
        if path.name != "iSerial":
            continue
        if path.exists():
            value = path.read_text().strip()
            if value:
                return value
    return ""


RESTART2_SYSCALL = 142
RESTART2_MAGIC1 = 0xFEE1DEAD
RESTART2_MAGIC2 = 672274793
RESTART2_BOOTLOADER = 0xA1B2C3D4


def restart2_bootloader(*, machine: str | None = None, syscall_fn=None) -> None:
    machine = (machine or platform.machine()).lower()
    if machine not in {"aarch64", "arm64"}:
        raise TrialError(f"Restart2 bootloader requires AArch64, found {machine!r}")
    if syscall_fn is None:
        libc = ctypes.CDLL(None, use_errno=True)
        libc.syscall.restype = ctypes.c_long
        libc.syscall.argtypes = [
            ctypes.c_long,
            ctypes.c_ulong,
            ctypes.c_ulong,
            ctypes.c_ulong,
            ctypes.c_void_p,
        ]
        syscall_fn = libc.syscall
    command = ctypes.create_string_buffer(b"bootloader\0")
    ctypes.set_errno(0)
    result = syscall_fn(
        RESTART2_SYSCALL,
        RESTART2_MAGIC1,
        RESTART2_MAGIC2,
        RESTART2_BOOTLOADER,
        ctypes.cast(command, ctypes.c_void_p),
    )
    errno = ctypes.get_errno()
    raise TrialError(
        f"Restart2 bootloader syscall returned {result!r}, errno={errno}"
    )


def _default_restart_bootloader() -> None:
    restart2_bootloader()


def _default_stop_service() -> dict:
    command = ["/usr/sbin/samurai-charging", "stop"]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=20,
    )
    if result.returncode != 0:
        raise TrialError(
            f"samurai-charging stop failed: {result.returncode}: {result.stderr.strip()}"
        )
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError:
        output = result.stdout.strip()
    return {
        "argv": command,
        "returncode": result.returncode,
        "stdout": output,
        "stderr": result.stderr.strip(),
    }


def _default_sync() -> None:
    if not hasattr(os, "sync"):
        raise TrialError("os.sync is unavailable")
    os.sync()


def _default_fsync(paths: list[Path]) -> None:
    for path in paths:
        path = Path(path)
        if not path.exists():
            raise TrialError(f"cannot fsync missing path: {path}")
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
        fd = os.open(path, flags)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def _sync() -> None:
    if hasattr(os, "sync"):
        os.sync()


class StageRuntime:
    def __init__(
        self,
        *,
        package: Path,
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
        serial_reader=_default_serial,
        service_stopper=_default_stop_service,
        syncer=_default_sync,
        fsyncer=_default_fsync,
        bootloader_restarter=_default_restart_bootloader,
    ) -> None:
        self.package = Path(package)
        self.root = Path(root)
        self.proc_root = Path(proc_root)
        self.sys_root = Path(sys_root)
        self.dev_root = Path(dev_root)
        self.target_root = Path(target_root)
        self.manifest_path = Path(manifest_path or self.package / "manifest.json")
        self.devices = {key: Path(value) for key, value in (devices or {}).items()}
        self.identities = identities or {}
        self.require_root = require_root
        self.strict_carrier_pins = strict_carrier_pins
        self.partition_bytes = dict(partition_bytes or PARTITION_BYTES)
        self.serial_reader = serial_reader
        self.service_stopper = service_stopper
        self.syncer = syncer
        self.fsyncer = fsyncer
        self.bootloader_restarter = bootloader_restarter

    def target(self, path: Path) -> Path:
        path = Path(path)
        if self.target_root == Path("/"):
            return path
        return self.target_root / path.relative_to("/")

    def device(self, name: str) -> Path:
        if name in self.devices:
            return self.devices[name]
        return self.dev_root / "disk/by-partlabel" / name


def load_package_manifest(rt: StageRuntime) -> dict:
    require_regular(rt.manifest_path, require_root=rt.require_root)
    manifest = read_json(rt.manifest_path)
    if manifest.get("schema") != 1 or manifest.get("trial_id") != TRIAL_ID:
        raise TrialError("unexpected trial manifest")
    if manifest.get("kernel_version") != VERSION:
        raise TrialError("unexpected kernel version pin")
    if manifest.get("watch_seconds") != WATCH_SECONDS or manifest.get("token") != TOKEN:
        raise TrialError("unexpected watchdog metadata")
    if manifest.get("high_voltage_permitted") is not False:
        raise TrialError("high voltage must remain disabled")
    files = manifest.get("device_files")
    if not isinstance(files, dict):
        raise TrialError("device_files missing")
    required_targets = {str(COMMON_PATH), str(GUARD_PATH), str(SERVICE_PATH)}
    if required_targets - {row.get("target") for row in files.values()}:
        raise TrialError("guard/common/service entries missing")
    for row in files.values():
        source = rt.package / row["source"]
        require_regular(source, require_root=rt.require_root)
        if sha256_file(source) != row["sha256"]:
            raise TrialError(f"package file hash mismatch: {source}")
    for name, size in rt.partition_bytes.items():
        row = manifest["carriers"][name]
        if row["bytes"] != size:
            raise TrialError(f"unexpected {name} carrier size")
        if rt.strict_carrier_pins and row["old"] != OLD_CARRIER_SHA256[name]:
            raise TrialError(f"unexpected {name} carrier pin")
    return manifest


def _partition_size(rt: StageRuntime, name: str) -> tuple[int, dict]:
    device = rt.device(name)
    if device.is_file():
        size = device.stat().st_size
    elif device.is_block_device():
        block = rt.sys_root / "class/block" / device.resolve().name
        sectors = int((block / "size").read_text().strip())
        size = sectors * 512
    else:
        raise TrialError(f"carrier device missing: {device}")
    if name in rt.identities:
        identity = rt.identities[name]
    else:
        resolved = device.resolve(strict=True)
        block = rt.sys_root / "class/block" / resolved.name
        aliases = []
        uuid_root = rt.dev_root / "disk/by-partuuid"
        if uuid_root.is_dir():
            for alias in uuid_root.iterdir():
                try:
                    if alias.resolve(strict=True) == resolved:
                        aliases.append(alias.name)
                except OSError:
                    continue
        if len(aliases) != 1:
            raise TrialError(f"expected one partuuid for {name}")
        identity = {
            "partuuid": aliases[0],
            "start": int((block / "start").read_text().strip()),
            "sectors": int((block / "size").read_text().strip()),
            "partition": int((block / "partition").read_text().strip()),
        }
    if size != rt.partition_bytes[name]:
        raise TrialError(f"unexpected partition size: {name}")
    return size, identity


def _backup_original_service(rt: StageRuntime) -> dict:
    source = rt.target(SERVICE_PATH)
    info = require_regular(source, require_root=rt.require_root)
    destination = rt.root / "original/samurai-charging"
    if destination.exists() or destination.is_symlink():
        raise TrialError("refusing to overwrite original service backup")
    digest = sha256_file(source)
    copy_verified(source, destination, expected_sha256=digest, mode=stat.S_IMODE(info.st_mode))
    return {
        "target": str(SERVICE_PATH),
        "sha256": digest,
        "mode": stat.S_IMODE(info.st_mode),
        "uid": info.st_uid,
        "gid": info.st_gid,
    }


def _inspect_original_service(rt: StageRuntime) -> dict:
    source = rt.target(SERVICE_PATH)
    info = require_regular(source, require_root=rt.require_root)
    return {
        "target": str(SERVICE_PATH),
        "sha256": sha256_file(source),
        "mode": stat.S_IMODE(info.st_mode),
        "uid": info.st_uid,
        "gid": info.st_gid,
    }


def _backup_old_carriers(rt: StageRuntime, expected_hashes: dict[str, str]) -> dict[str, str]:
    hashes = {}
    for name, size in rt.partition_bytes.items():
        device = rt.device(name)
        actual = sha256_file(device)
        if actual != expected_hashes[name]:
            raise TrialError(f"current {name} is not the pinned old carrier")
        target = rt.root / "old" / f"{name}.img"
        if target.exists() or target.is_symlink():
            raise TrialError(f"refusing to overwrite old carrier backup: {name}")
        copy_verified(
            device,
            target,
            expected_sha256=actual,
            expected_bytes=size,
        )
        hashes[name] = actual
    return hashes


def _install_file(rt: StageRuntime, row: dict) -> str:
    source = rt.package / row["source"]
    target = rt.target(Path(row["target"]))
    mode = int(row.get("mode", 0o644))
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != row["sha256"]:
        raise TrialError(f"source changed before install: {source}")
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
    atomic_write(target, raw, mode)
    require_regular(target, require_root=rt.require_root)
    if sha256_file(target) != row["sha256"]:
        raise TrialError(f"installed file hash mismatch: {target}")
    return str(target)


def stage(rt: StageRuntime, *, execute: bool, operator_serial: str | None = None) -> dict:
    if rt.require_root and not _is_root():
        raise TrialError("root is required")
    os.umask(0o077)
    rt.root.mkdir(parents=True, exist_ok=True, mode=0o700)
    if rt.require_root and rt.root.stat().st_mode & 0o077:
        raise TrialError("private trial directory is too open")
    lock_path = rt.root / "stage.lock"
    lock_fd = None
    try:
        if fcntl is not None:
            lock_fd = os.open(
                lock_path,
                os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0),
                0o600,
            )
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise TrialError("another stage process is active") from error
        if (rt.root / "stage-result.json").exists():
            raise TrialError("stage already completed")

        manifest = load_package_manifest(rt)
        if operator_serial is not None:
            serial = operator_serial.strip()
            serial_source = "operator_cli"
        else:
            serial = rt.serial_reader().strip()
            serial_source = "device_property" if serial else "unavailable"
        if not serial:
            raise TrialError("device serial unavailable; rerun with --serial 62bc28a1")
        required_serial = manifest["fastboot"]["serial"].lower()
        if serial.lower() != required_serial:
            raise TrialError(f"unexpected device serial: {serial!r}")
        boot = (rt.proc_root / "sys/kernel/random/boot_id").read_text().strip()
        version = (rt.proc_root / "version").read_text().strip()
        if VERSION in version:
            raise TrialError("stage must run from the pre-trial kernel")

        identities = {}
        for name in rt.partition_bytes:
            _, identities[name] = _partition_size(rt, name)
        if execute:
            original_service = _backup_original_service(rt)
            old_hashes = _backup_old_carriers(
                rt, {name: manifest["carriers"][name]["old"] for name in rt.partition_bytes}
            )
        else:
            original_service = _inspect_original_service(rt)
            old_hashes = {}
            for name in rt.partition_bytes:
                actual = sha256_file(rt.device(name))
                if actual != manifest["carriers"][name]["old"]:
                    raise TrialError(f"current {name} is not the pinned old carrier")
                old_hashes[name] = actual

        plan = {
            "schema": 1,
            "trial_id": TRIAL_ID,
            "boot_id": boot,
            "kernel_version": version,
            "serial": serial,
            "serial_source": serial_source,
            "partition_identity": identities,
            "old_carriers": old_hashes,
            "original_service": original_service,
            "installs_carriers": False,
            "execute_requested": bool(execute),
        }
        service_stop = None
        preinstall_fsync_paths = []
        if execute:
            # Stop the existing charging service before any guard/service
            # installation, then make the rollback evidence durable.
            service_stop = rt.service_stopper()
            plan["service_stop"] = service_stop
            plan["preinstall_fsync_paths"] = [
                str(rt.root / "stage-plan.json"),
                str(rt.root / "original/samurai-charging"),
                str(rt.root / "old/boot.img"),
                str(rt.root / "old/logdump.img"),
                str(rt.manifest_path),
            ]
        atomic_write(
            rt.root / "stage-plan.json",
            (json.dumps(plan, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        )
        if execute:
            rt.syncer()
            preinstall_fsync_paths = [
                Path(rt.root / "stage-plan.json"),
                rt.root / "original/samurai-charging",
                rt.root / "old/boot.img",
                rt.root / "old/logdump.img",
                rt.manifest_path,
                rt.root,
                rt.root / "original",
                rt.root / "old",
            ]
            rt.fsyncer(preinstall_fsync_paths)

        installed = []
        ordered = sorted(
            manifest["device_files"].items(),
            key=lambda item: item[1]["target"] == str(MANIFEST_PATH),
        )
        if execute:
            for _, row in ordered:
                installed.append(_install_file(rt, row))
            manifest_target = rt.target(MANIFEST_PATH)
            manifest_target.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
            atomic_write(manifest_target, rt.manifest_path.read_bytes(), 0o644)
            installed.append(str(manifest_target))
        manifest_hash = sha256_file(rt.manifest_path)
        receipt = {
            "schema": 1,
            "trial_id": TRIAL_ID,
            "passed": True,
            "boot_id": boot,
            "kernel_version": version,
            "serial": serial,
            "serial_source": serial_source,
            "version_pin": VERSION,
            "watch_seconds": WATCH_SECONDS,
            "guard_installed": bool(execute),
            "original_service_installed": bool(execute),
            "old_carriers_backed_up": bool(execute),
            "old_carrier_sha256": old_hashes,
            "partition_identity_recorded": True,
            "partition_identity": identities,
            "original_service": original_service,
            "manifest_sha256": manifest_hash,
            "installed_file_sha256": {
                row["target"]: row["sha256"] for row in manifest["device_files"].values()
            },
            "new_carrier_written": False,
            "host_carrier_write_required": True,
            "reboot_bootloader_requested": False,
            "stage_execute": bool(execute),
            "service_stop": service_stop,
            "preinstall_sync_fsync": [
                str(path) for path in preinstall_fsync_paths
            ],
            "restart_method": "restart2_syscall_142",
            "restart2": {
                "syscall": RESTART2_SYSCALL,
                "magic1": RESTART2_MAGIC1,
                "magic2": RESTART2_MAGIC2,
                "command": "bootloader",
                "command_value": RESTART2_BOOTLOADER,
                "attempt_count": 1 if execute else 0,
                "retry": False,
            },
        }
        if not execute:
            atomic_write(
                rt.root / "stage-preflight.json",
                (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8"),
            )
            print(json.dumps(receipt, sort_keys=True))
            return receipt

        receipt["reboot_bootloader_requested"] = True
        postinstall_paths = [
            Path(rt.root / "stage.json"),
            Path(rt.root / "stage-result.json"),
            rt.target(MANIFEST_PATH),
            *(rt.target(Path(row["target"])) for row in manifest["device_files"].values()),
        ]
        receipt["postinstall_sync_fsync"] = [
            str(path) for path in postinstall_paths
        ]
        atomic_write(
            rt.root / "stage.json",
            (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        )
        atomic_write(
            rt.root / "stage-result.json",
            (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        )
        rt.syncer()
        rt.fsyncer(postinstall_paths)
        print(json.dumps(receipt, sort_keys=True), flush=True)
        _sync()
        try:
            rt.bootloader_restarter()
        except BaseException:
            # No carrier was written.  Put the original wrapper back before
            # returning failure so the failed stage is not left armed.
            original = rt.root / "original/samurai-charging"
            target = rt.target(SERVICE_PATH)
            info = require_regular(original, require_root=rt.require_root)
            atomic_write(target, original.read_bytes(), stat.S_IMODE(info.st_mode))
            if _is_root():
                os.chown(target, info.st_uid, info.st_gid)
            raise
        return receipt
    finally:
        if lock_fd is not None:
            os.close(lock_fd)


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--serial")
    parser.add_argument("--package", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args(argv)
    receipt = stage(
        StageRuntime(package=args.package),
        execute=args.execute,
        operator_serial=args.serial,
    )
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(_main())
