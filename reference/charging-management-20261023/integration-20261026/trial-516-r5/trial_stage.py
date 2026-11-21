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
    DEVICE_FILE_SPECS,
    DEVICE_ROOT,
    GUARD_PATH,
    MAIN_MANIFEST_PATH,
    MAIN_MANIFEST_SHA256,
    MANIFEST_PATH,
    MODULE_MODE,
    MODULE_NAME,
    MODULE_NEW_BYTES,
    MODULE_NEW_SHA256,
    MODULE_OLD_BYTES,
    MODULE_OLD_SHA256,
    MODULE_PATH,
    MODULE_SOURCE,
    OLD_CARRIER_SHA256,
    PARTITION_BYTES,
    RUNLEVEL_ADD_ARGV,
    RUNLEVEL_DIR,
    SERVICE_PATH,
    TOKEN,
    TRIAL_ID,
    VERSION,
    WATCH_SECONDS,
    TrialError,
    atomic_write,
    copy_verified,
    inspect_service_runlevel,
    read_json,
    require_regular,
    restore_service_runlevel,
    sha256_file,
    validate_service_runlevel,
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


def _default_inspect_service_runlevel(rt: "StageRuntime") -> dict:
    return inspect_service_runlevel(
        rt.target_root,
        require_root=rt.require_root,
    )


def _default_enable_service_runlevel(
    rt: "StageRuntime", inspected: dict
) -> dict:
    record = validate_service_runlevel(inspected)
    current = _default_inspect_service_runlevel(rt)
    if current != record:
        raise TrialError("runlevel state changed before service enable")
    if record["before"] == "enabled":
        return record
    command = list(RUNLEVEL_ADD_ARGV)
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=20,
    )
    if result.returncode != 0:
        raise TrialError(
            f"rc-update add samurai-charging default failed: "
            f"{result.returncode}: {result.stderr.strip()}"
        )
    # The command succeeded, so this stage owns the new link from this point on.
    record["added"] = True
    actual = _default_inspect_service_runlevel(rt)
    if actual["before"] != "enabled":
        raise TrialError("rc-update succeeded but the default runlevel link is missing")
    record["link_target"] = actual["link_target"]
    record["verified"] = True
    record["command"] = {
        "argv": command,
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }
    rt.fsyncer([rt.target(RUNLEVEL_DIR)])
    return validate_service_runlevel(record)


def _default_restore_service_runlevel(
    rt: "StageRuntime", record: object
) -> dict:
    return restore_service_runlevel(
        rt.target_root,
        record,
        fsync_directory=lambda path: rt.fsyncer([path]),
    )


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
        runlevel_inspector=None,
        runlevel_enabler=None,
        runlevel_restorer=None,
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
        self.runlevel_inspector = runlevel_inspector or _default_inspect_service_runlevel
        self.runlevel_enabler = runlevel_enabler or _default_enable_service_runlevel
        self.runlevel_restorer = runlevel_restorer or _default_restore_service_runlevel

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
    expected_files = {
        str(target): (source, mode)
        for target, (source, mode) in DEVICE_FILE_SPECS.items()
    }
    if set(files) != set(expected_files):
        raise TrialError("device_files must contain exactly the formal trial files")
    for target, row in files.items():
        if not isinstance(row, dict) or row.get("target") != target:
            raise TrialError(f"device_files target mismatch: {target}")
        expected_source, expected_mode = expected_files[target]
        if row.get("source") != expected_source or row.get("mode") != expected_mode:
            raise TrialError(f"unexpected device_files source/mode: {target}")
        source = rt.package / row["source"]
        require_regular(source, require_root=rt.require_root)
        if sha256_file(source) != row["sha256"]:
            raise TrialError(f"package file hash mismatch: {source}")
    module = manifest.get("kernel_module")
    if not isinstance(module, dict):
        raise TrialError("kernel_module metadata missing")
    expected_module_keys = {
        "name",
        "source",
        "target",
        "mode",
        "old_sha256",
        "old_bytes",
        "new_sha256",
        "new_bytes",
    }
    if set(module) != expected_module_keys:
        raise TrialError("kernel_module metadata has unexpected fields")
    if (
        module.get("name") != MODULE_NAME
        or module.get("source") != MODULE_SOURCE
        or module.get("target") != MODULE_PATH.as_posix()
        or module.get("mode") != MODULE_MODE
    ):
        raise TrialError("unexpected kernel_module source/target/mode")
    if not isinstance(module.get("old_sha256"), str) or len(module["old_sha256"]) != 64:
        raise TrialError("invalid original module hash")
    if not isinstance(module.get("new_sha256"), str) or len(module["new_sha256"]) != 64:
        raise TrialError("invalid replacement module hash")
    if type(module.get("old_bytes")) is not int or type(module.get("new_bytes")) is not int:
        raise TrialError("invalid module size")
    module_source = rt.package / module["source"]
    require_regular(module_source, require_root=rt.require_root)
    if module_source.stat().st_size != module["new_bytes"]:
        raise TrialError("replacement module size mismatch")
    if sha256_file(module_source) != module["new_sha256"]:
        raise TrialError("replacement module hash mismatch")
    if rt.strict_carrier_pins and (
        module["old_sha256"] != MODULE_OLD_SHA256
        or module["old_bytes"] != MODULE_OLD_BYTES
        or module["new_sha256"] != MODULE_NEW_SHA256
        or module["new_bytes"] != MODULE_NEW_BYTES
    ):
        raise TrialError("unexpected kernel_module pin")
    main_manifest = manifest.get("main_manifest")
    if not isinstance(main_manifest, dict):
        raise TrialError("main_manifest metadata missing")
    if main_manifest.get("target") != MAIN_MANIFEST_PATH.as_posix():
        raise TrialError("unexpected main manifest target")
    if main_manifest.get("service_target") != SERVICE_PATH.as_posix():
        raise TrialError("unexpected main manifest service target")
    if (
        rt.strict_carrier_pins
        and main_manifest.get("old_sha256") != MAIN_MANIFEST_SHA256
    ):
        raise TrialError("unexpected main manifest pin")
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
        "target": SERVICE_PATH.as_posix(),
        "sha256": digest,
        "mode": stat.S_IMODE(info.st_mode),
        "uid": info.st_uid,
        "gid": info.st_gid,
    }


def _inspect_original_service(rt: StageRuntime) -> dict:
    source = rt.target(SERVICE_PATH)
    info = require_regular(source, require_root=rt.require_root)
    return {
        "target": SERVICE_PATH.as_posix(),
        "sha256": sha256_file(source),
        "mode": stat.S_IMODE(info.st_mode),
        "uid": info.st_uid,
        "gid": info.st_gid,
    }


def _device_backup_path(rt: StageRuntime, target: str) -> Path:
    name = target.lstrip("/").replace("/", "__")
    return rt.root / "original/device-files" / name


def _inspect_original_device_files(rt: StageRuntime, manifest: dict) -> dict:
    original = {}
    for target, row in manifest["device_files"].items():
        if target == SERVICE_PATH.as_posix():
            continue
        path = rt.target(Path(target))
        try:
            info = path.lstat()
        except FileNotFoundError:
            original[target] = {
                "target": target,
                "state": "missing",
                "sha256": None,
                "bytes": None,
                "mode": None,
                "uid": None,
                "gid": None,
                "backup": None,
            }
            continue
        if not stat.S_ISREG(info.st_mode):
            raise TrialError(f"device file target is not a regular file: {path}")
        require_regular(
            path,
            require_root=rt.require_root,
            max_mode=int(row["mode"]),
        )
        original[target] = {
            "target": target,
            "state": "file",
            "sha256": sha256_file(path),
            "bytes": info.st_size,
            "mode": stat.S_IMODE(info.st_mode),
            "uid": info.st_uid,
            "gid": info.st_gid,
            "backup": None,
        }
    return original


def _backup_original_device_files(
    rt: StageRuntime,
    inspected: dict,
) -> dict:
    (rt.root / "original/device-files").mkdir(parents=True, exist_ok=True, mode=0o700)
    original = {}
    for target, row in inspected.items():
        value = dict(row)
        if value["state"] == "file":
            source = rt.target(Path(target))
            destination = _device_backup_path(rt, target)
            if destination.exists() or destination.is_symlink():
                raise TrialError(f"refusing to overwrite device file backup: {target}")
            if (
                source.stat().st_size != value["bytes"]
                or sha256_file(source) != value["sha256"]
            ):
                raise TrialError(f"original device file changed before backup: {target}")
            copy_verified(
                source,
                destination,
                expected_sha256=value["sha256"],
                expected_bytes=value["bytes"],
                mode=value["mode"],
            )
            value["backup"] = str(destination)
        original[target] = value
    return original


def _inspect_original_module(rt: StageRuntime, manifest: dict) -> dict:
    row = manifest["kernel_module"]
    source = rt.target(Path(row["target"]))
    info = require_regular(source, require_root=rt.require_root, max_mode=MODULE_MODE)
    digest = sha256_file(source)
    if info.st_size != row["old_bytes"]:
        raise TrialError("original module size mismatch")
    if digest != row["old_sha256"]:
        raise TrialError("original module hash mismatch")
    return {
        "name": row["name"],
        "target": row["target"],
        "sha256": digest,
        "bytes": info.st_size,
        "mode": stat.S_IMODE(info.st_mode),
        "uid": info.st_uid,
        "gid": info.st_gid,
    }


def _inspect_original_main_manifest(
    rt: StageRuntime, manifest: dict, service_sha256: str
) -> tuple[dict, dict]:
    pin = manifest["main_manifest"]
    source = rt.target(Path(pin["target"]))
    info = require_regular(source, require_root=rt.require_root)
    digest = sha256_file(source)
    if digest != pin["old_sha256"]:
        raise TrialError("main manifest hash mismatch")
    value = read_json(source)
    installed = value.get("installed_files")
    if not isinstance(installed, dict):
        raise TrialError("main manifest installed_files missing")
    if installed.get(pin["service_target"]) != service_sha256:
        raise TrialError("main manifest does not pin the original service")
    module = manifest["kernel_module"]
    modules = value.get("modules")
    if not isinstance(modules, dict):
        raise TrialError("main manifest modules missing")
    module_value = modules.get(module["name"])
    if not isinstance(module_value, dict):
        raise TrialError("main manifest module entry missing")
    if (
        module_value.get("target") != module["target"]
        or module_value.get("sha256") != module["old_sha256"]
    ):
        raise TrialError("main manifest does not pin the original module")
    if installed.get(module["target"]) != module["old_sha256"]:
        raise TrialError("main manifest installed_files does not pin the original module")
    return (
        {
            "target": pin["target"],
            "sha256": digest,
            "mode": stat.S_IMODE(info.st_mode),
            "uid": info.st_uid,
            "gid": info.st_gid,
            "service_target": pin["service_target"],
            "module_target": module["target"],
        },
        value,
    )


def _backup_original_main_manifest(
    rt: StageRuntime,
    inspected: dict,
    value: dict,
    service_sha256: str,
) -> dict:
    source = rt.target(Path(inspected["target"]))
    destination = rt.root / "original/main-manifest.json"
    installed = value.get("installed_files")
    if not isinstance(installed, dict):
        raise TrialError("original main manifest changed before backup")
    if installed.get(inspected["service_target"]) != service_sha256:
        raise TrialError("original main manifest service binding changed")
    module_target = inspected["module_target"]
    modules = value.get("modules")
    if not isinstance(modules, dict):
        raise TrialError("original main manifest modules changed")
    module_value = modules.get(MODULE_NAME)
    if not isinstance(module_value, dict):
        raise TrialError("original main manifest module binding changed")
    if (
        module_value.get("target") != module_target
        or module_value.get("sha256") != installed.get(module_target)
    ):
        raise TrialError("original main manifest module binding changed")
    if destination.exists() or destination.is_symlink():
        raise TrialError("refusing to overwrite original main manifest backup")
    copy_verified(
        source,
        destination,
        expected_sha256=inspected["sha256"],
        mode=inspected["mode"],
    )
    return {**inspected, "backup": str(destination)}


def _backup_original_module(
    rt: StageRuntime, manifest: dict, inspected: dict
) -> dict:
    row = manifest["kernel_module"]
    source = rt.target(Path(row["target"]))
    info = require_regular(source, require_root=rt.require_root, max_mode=MODULE_MODE)
    if (
        info.st_size != inspected["bytes"]
        or sha256_file(source) != inspected["sha256"]
    ):
        raise TrialError("original module changed before backup")
    destination = rt.root / "original/samurai-mp2650.ko"
    if destination.exists() or destination.is_symlink():
        raise TrialError("refusing to overwrite original module backup")
    copy_verified(
        source,
        destination,
        expected_sha256=inspected["sha256"],
        expected_bytes=inspected["bytes"],
        mode=inspected["mode"],
    )
    return {**inspected, "backup": str(destination)}


def _patched_main_manifest(manifest: dict, value: dict) -> tuple[bytes, str]:
    pin = manifest["main_manifest"]
    patched = json.loads(json.dumps(value))
    installed = patched.get("installed_files")
    if not isinstance(installed, dict):
        raise TrialError("main manifest installed_files missing")
    for target, row in manifest["device_files"].items():
        installed[target] = row["sha256"]
    module = manifest["kernel_module"]
    modules = patched.get("modules")
    if not isinstance(modules, dict):
        raise TrialError("main manifest modules missing")
    module_value = modules.get(module["name"])
    if not isinstance(module_value, dict):
        raise TrialError("main manifest module entry missing")
    if (
        module_value.get("target") != module["target"]
        or module_value.get("sha256") != module["old_sha256"]
    ):
        raise TrialError("main manifest module pin changed before patch")
    if installed.get(module["target"]) != module["old_sha256"]:
        raise TrialError("main manifest installed module pin changed before patch")
    module_value["sha256"] = module["new_sha256"]
    installed[module["target"]] = module["new_sha256"]
    raw = (json.dumps(patched, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )
    return raw, hashlib.sha256(raw).hexdigest()


def _restore_main_manifest(rt: StageRuntime, original: dict) -> None:
    backup = rt.root / "original/main-manifest.json"
    info = require_regular(backup, require_root=rt.require_root)
    if sha256_file(backup) != original["sha256"]:
        raise TrialError("original main manifest backup hash mismatch")
    target = rt.target(Path(original["target"]))
    atomic_write(target, backup.read_bytes(), stat.S_IMODE(info.st_mode))
    if _is_root():
        os.chown(target, info.st_uid, info.st_gid)
    if sha256_file(target) != original["sha256"]:
        raise TrialError("original main manifest readback mismatch")


def _restore_original_module(rt: StageRuntime, original: dict) -> None:
    backup = rt.root / "original/samurai-mp2650.ko"
    info = require_regular(backup, require_root=rt.require_root)
    if (
        info.st_size != original["bytes"]
        or sha256_file(backup) != original["sha256"]
    ):
        raise TrialError("original module backup hash mismatch")
    target = rt.target(Path(original["target"]))
    atomic_write(target, backup.read_bytes(), stat.S_IMODE(info.st_mode))
    if _is_root():
        os.chown(target, info.st_uid, info.st_gid)
    if (
        target.stat().st_size != original["bytes"]
        or sha256_file(target) != original["sha256"]
    ):
        raise TrialError("original module readback mismatch")


def _restore_original_device_files(
    rt: StageRuntime,
    manifest: dict,
    original: dict,
) -> None:
    for target, row in original.items():
        if target == SERVICE_PATH.as_posix():
            continue
        path = rt.target(Path(target))
        installed_hash = manifest["device_files"][target]["sha256"]
        if row.get("state") == "missing":
            try:
                info = path.lstat()
            except FileNotFoundError:
                continue
            if not stat.S_ISREG(info.st_mode) or sha256_file(path) != installed_hash:
                raise TrialError(f"new device file changed before rollback: {target}")
            path.unlink()
            continue
        if row.get("state") != "file":
            raise TrialError(f"invalid original device file state: {target}")
        backup = Path(str(row.get("backup") or ""))
        info = require_regular(backup, require_root=rt.require_root)
        if (
            info.st_size != row["bytes"]
            or sha256_file(backup) != row["sha256"]
        ):
            raise TrialError(f"original device file backup hash mismatch: {target}")
        atomic_write(path, backup.read_bytes(), stat.S_IMODE(info.st_mode))
        if _is_root():
            os.chown(path, info.st_uid, info.st_gid)
        if (
            path.stat().st_size != row["bytes"]
            or sha256_file(path) != row["sha256"]
        ):
            raise TrialError(f"original device file readback mismatch: {target}")


def _restore_stage_files(
    rt: StageRuntime,
    manifest: dict,
    original_service: dict,
    original_device_files: dict,
    original_module: dict,
    original_main_manifest: dict,
    service_runlevel: dict,
) -> None:
    _restore_original_module(rt, original_module)
    _restore_main_manifest(rt, original_main_manifest)
    service_backup = rt.root / "original/samurai-charging"
    info = require_regular(service_backup, require_root=rt.require_root)
    if sha256_file(service_backup) != original_service["sha256"]:
        raise TrialError("original service backup hash mismatch")
    service_target = rt.target(SERVICE_PATH)
    atomic_write(service_target, service_backup.read_bytes(), stat.S_IMODE(info.st_mode))
    if _is_root():
        os.chown(service_target, info.st_uid, info.st_gid)
    _restore_original_device_files(rt, manifest, original_device_files)
    trial_manifest = rt.target(MANIFEST_PATH)
    try:
        if trial_manifest.is_file() and not trial_manifest.is_symlink():
            trial_manifest.unlink()
    except FileNotFoundError:
        pass
    rt.runlevel_restorer(rt, service_runlevel)
    rt.syncer()


def _record_stage_failure(
    rt: StageRuntime, *, boot_id: str, error: BaseException
) -> None:
    atomic_write(
        rt.root / "stage-failure.json",
        (
            json.dumps(
                {
                    "schema": 1,
                    "trial_id": TRIAL_ID,
                    "boot_id": boot_id,
                    "restored_original_files": True,
                    "error": f"{type(error).__name__}: {error}",
                },
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8"),
    )
    for name in ("stage.json", "stage-result.json"):
        try:
            (rt.root / name).unlink()
        except FileNotFoundError:
            pass
    rt.syncer()


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


def _install_module(rt: StageRuntime, manifest: dict) -> str:
    row = manifest["kernel_module"]
    source = rt.package / row["source"]
    target = rt.target(Path(row["target"]))
    raw = source.read_bytes()
    if (
        len(raw) != row["new_bytes"]
        or hashlib.sha256(raw).hexdigest() != row["new_sha256"]
    ):
        raise TrialError(f"replacement module changed before install: {source}")
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
    atomic_write(target, raw, row["mode"])
    require_regular(target, require_root=rt.require_root, max_mode=MODULE_MODE)
    if (
        target.stat().st_size != row["new_bytes"]
        or sha256_file(target) != row["new_sha256"]
    ):
        raise TrialError(f"installed module hash mismatch: {target}")
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

        service_runlevel = validate_service_runlevel(rt.runlevel_inspector(rt))
        identities = {}
        for name in rt.partition_bytes:
            _, identities[name] = _partition_size(rt, name)
        original_service = _inspect_original_service(rt)
        original_main_manifest, original_main_value = _inspect_original_main_manifest(
            rt, manifest, original_service["sha256"]
        )
        original_module = _inspect_original_module(rt, manifest)
        original_device_files = _inspect_original_device_files(rt, manifest)
        service_row = manifest["device_files"][SERVICE_PATH.as_posix()]
        module_row = manifest["kernel_module"]
        patched_main_bytes, patched_main_sha256 = _patched_main_manifest(
            manifest, original_main_value
        )
        if execute:
            original_service = _backup_original_service(rt)
            original_device_files = _backup_original_device_files(
                rt,
                original_device_files,
            )
            original_main_manifest = _backup_original_main_manifest(
                rt,
                original_main_manifest,
                original_main_value,
                original_service["sha256"],
            )
            original_module = _backup_original_module(
                rt,
                manifest,
                original_module,
            )
            old_hashes = _backup_old_carriers(
                rt, {name: manifest["carriers"][name]["old"] for name in rt.partition_bytes}
            )
        else:
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
            "original_device_files": original_device_files,
            "original_module": original_module,
            "original_main_manifest": original_main_manifest,
            "service_runlevel": service_runlevel,
            "main_manifest_patch": {
                "target": MAIN_MANIFEST_PATH.as_posix(),
                "old_sha256": original_main_manifest["sha256"],
                "new_sha256": patched_main_sha256,
                "service_target": SERVICE_PATH.as_posix(),
                "service_sha256": service_row["sha256"],
                "device_files_sha256": {
                    target: row["sha256"]
                    for target, row in manifest["device_files"].items()
                },
                "module_name": module_row["name"],
                "module_target": module_row["target"],
                "module_old_sha256": module_row["old_sha256"],
                "module_new_sha256": module_row["new_sha256"],
            },
            "installs_carriers": False,
            "execute_requested": bool(execute),
            "host_fetch_unavailable": bool(
                manifest["fastboot"].get("host_fetch_unavailable", False)
            ),
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
                str(rt.root / "original/device-files"),
                str(rt.root / "original/samurai-mp2650.ko"),
                str(rt.root / "original/main-manifest.json"),
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
                rt.root / "original/device-files",
                rt.root / "original/samurai-mp2650.ko",
                rt.root / "original/main-manifest.json",
                rt.root / "old/boot.img",
                rt.root / "old/logdump.img",
                rt.manifest_path,
                rt.root,
                rt.root / "original",
                rt.root / "old",
            ]
            rt.fsyncer(preinstall_fsync_paths)

        installed = []
        if execute:
            try:
                for row in manifest["device_files"].values():
                    installed.append(_install_file(rt, row))
                installed.append(_install_module(rt, manifest))
                service_runlevel = validate_service_runlevel(
                    rt.runlevel_enabler(rt, service_runlevel)
                )
                main_target = rt.target(MAIN_MANIFEST_PATH)
                main_target.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
                atomic_write(
                    main_target,
                    patched_main_bytes,
                    original_main_manifest["mode"],
                )
                if _is_root():
                    os.chown(
                        main_target,
                        original_main_manifest["uid"],
                        original_main_manifest["gid"],
                    )
                if sha256_file(main_target) != patched_main_sha256:
                    raise TrialError("patched main manifest readback mismatch")
                installed.append(str(main_target))
                manifest_target = rt.target(MANIFEST_PATH)
                manifest_target.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
                atomic_write(manifest_target, rt.manifest_path.read_bytes(), 0o644)
                installed.append(str(manifest_target))
            except BaseException as error:
                _restore_stage_files(
                    rt,
                    manifest,
                    original_service,
                    original_device_files,
                    original_module,
                    original_main_manifest,
                    service_runlevel,
                )
                _record_stage_failure(rt, boot_id=boot, error=error)
                raise
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
            "device_files_backed_up": bool(execute),
            "original_service_installed": bool(execute),
            "module_installed": bool(execute),
            "main_manifest_patched": bool(execute),
            "old_carriers_backed_up": bool(execute),
            "old_carrier_sha256": old_hashes,
            "partition_identity_recorded": True,
            "partition_identity": identities,
            "original_service": original_service,
            "original_device_files": original_device_files,
            "original_module": original_module,
            "original_main_manifest": original_main_manifest,
            "service_runlevel": service_runlevel,
            "main_manifest_patch": {
                "target": MAIN_MANIFEST_PATH.as_posix(),
                "old_sha256": original_main_manifest["sha256"],
                "new_sha256": patched_main_sha256,
                "service_target": SERVICE_PATH.as_posix(),
                "service_sha256": service_row["sha256"],
                "device_files_sha256": {
                    target: row["sha256"]
                    for target, row in manifest["device_files"].items()
                },
                "module_name": module_row["name"],
                "module_target": module_row["target"],
                "module_old_sha256": module_row["old_sha256"],
                "module_new_sha256": module_row["new_sha256"],
            },
            "manifest_sha256": manifest_hash,
            "installed_file_sha256": {
                **{
                    row["target"]: row["sha256"]
                    for row in manifest["device_files"].values()
                },
                MODULE_PATH.as_posix(): module_row["new_sha256"],
                MAIN_MANIFEST_PATH.as_posix(): patched_main_sha256,
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
            "host_fetch_unavailable": bool(
                manifest["fastboot"].get("host_fetch_unavailable", False)
            ),
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
            rt.target(MAIN_MANIFEST_PATH),
            rt.target(RUNLEVEL_DIR),
            *(rt.target(Path(row["target"])) for row in manifest["device_files"].values()),
            rt.target(MODULE_PATH),
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
        except BaseException as error:
            # No carrier was written. Restore the exact service and main
            # manifest before returning so the failed stage is not left armed.
            _restore_stage_files(
                rt,
                manifest,
                original_service,
                original_device_files,
                original_module,
                original_main_manifest,
                service_runlevel,
            )
            _record_stage_failure(rt, boot_id=boot, error=error)
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
