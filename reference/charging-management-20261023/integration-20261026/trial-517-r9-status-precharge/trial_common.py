"""Shared constants and filesystem primitives for the #528 trial.

This module is intentionally free of device discovery and command execution so
the guard, stage helper, and local control tests can all use the same rules.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import struct
from pathlib import Path


TRIAL_ID = "charging-integration-r9-status-precharge-20261027"
TOKEN = "62a924fc0bdacd75e49429130cc7516d7de545cfa98a111e45a3e484915bb914"
VERSION = "#528 SMP PREEMPT Tue Oct 27 08:49:26 CST 2026"
RELEASE = "7.3.0-rc6-rmx1931-samurai-k363+"
WATCH_SECONDS = 300
EXPECTED_TAINTED = 4096

DEVICE_ROOT = Path(
    "/root/charging-management-20261023/trial-517-r9-status-precharge"
)
GUARD_PATH = Path("/usr/lib/samurai-charging/trial_guard.py")
COMMON_PATH = Path("/usr/lib/samurai-charging/trial_common.py")
POSTBOOT_AUDIT_PATH = Path("/usr/lib/samurai-charging/postboot_audit.py")
AUTOAUDIT_PATH = Path("/usr/lib/samurai-charging/trial_autoaudit.py")
SERVICE_PATH = Path("/etc/init.d/samurai-charging")
RUNLEVEL_DIR = Path("/etc/runlevels/default")
RUNLEVEL_PATH = RUNLEVEL_DIR / "samurai-charging"
RUNLEVEL_ADD_ARGV = ("/sbin/rc-update", "add", "samurai-charging", "default")
MAIN_MANIFEST_PATH = Path("/usr/share/samurai-charging/manifest.json")
MANIFEST_PATH = Path("/usr/share/samurai-charging/trial-manifest.json")
MAIN_MANIFEST_SHA256 = (
    "b07f7b4bda544a9631ce682221f1e78601d9b38e78d3151e8ac294b57873272d"
)
AUTO_ACCEPTANCE_NAME = "auto-acceptance.json"
AUTO_AUDIT_REPORT_NAME = "auto-audit-report.json"
AUTO_AUDIT_LAST_NAME = "auto-audit-last.json"
ACCEPTED_NAME = "accepted.json"
DEVICE_FILE_SPECS = {
    COMMON_PATH.as_posix(): ("trial_common.py", 0o644),
    GUARD_PATH.as_posix(): ("trial_guard.py", 0o755),
    POSTBOOT_AUDIT_PATH.as_posix(): ("postboot_audit.py", 0o644),
    AUTOAUDIT_PATH.as_posix(): ("trial_autoaudit.py", 0o755),
    SERVICE_PATH.as_posix(): ("service/samurai-charging", 0o755),
}

MODULE_NAME = "samurai-mp2650"
MODULE_SOURCE = "modules/samurai-mp2650.ko"
MODULE_PATH = Path(
    "/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/"
    "samurai-mp2650.ko"
)
MODULE_MODE = 0o644
MODULE_OLD_SHA256 = (
    "04da6a7bf492e44d6afa533816e662d54b5a5f0391f4fe0e5e6e7f8555cedf69"
)
MODULE_OLD_BYTES = 164360
MODULE_NEW_SHA256 = (
    "dbe445cfef6e095f8d028034f0fbba9231484b6510ab6f60354c6ff55e9c23d1"
)
MODULE_NEW_BYTES = 172000
MODULE_ENTRY_KEYS = frozenset(
    {
        "name",
        "source",
        "target",
        "mode",
        "old_sha256",
        "old_bytes",
        "new_sha256",
        "new_bytes",
    }
)
AUXILIARY_MODULE_SPECS = (
    {
        "name": "samurai-usb-input",
        "source": "modules/samurai-usb-input.ko",
        "target": (
            "/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/"
            "extra/samurai-charging/samurai-usb-input.ko"
        ),
        "mode": 0o600,
        "old_sha256": (
            "161bcc3376864e6f867aa5cc0371b5ab61ba9d716108aad0f45e6c765d378f86"
        ),
        "old_bytes": 26128,
        "new_sha256": (
            "22604106772b89758ea745531e99dd70a6ab696b7740705107a767599e9a6529"
        ),
        "new_bytes": 91896,
    },
)


def manifest_modules(manifest: dict) -> list[dict]:
    """Return the primary and optional auxiliary module records."""
    rows = [manifest.get("kernel_module")]
    auxiliary = manifest.get("auxiliary_kernel_modules", [])
    if not isinstance(auxiliary, list):
        raise TrialError("auxiliary_kernel_modules must be a list")
    rows.extend(auxiliary)
    if any(not isinstance(row, dict) for row in rows):
        raise TrialError("module metadata missing")
    return rows

PARTITION_BYTES = {
    "boot": 100663296,
    "logdump": 67108864,
}

NEW_CARRIER_SHA256 = {
    "boot": "13c98860646fa80241a0a042e17781fceb7873f13263c69433839fd11ab9f756",
    "logdump": "b91279466383d04ec17fbdb75d6e08bf2bb4be16d38d383083ee52f8e1dd67b1",
}
OLD_CARRIER_SHA256 = {
    "boot": "13c98860646fa80241a0a042e17781fceb7873f13263c69433839fd11ab9f756",
    "logdump": "d884075a04d00112c95d0d3215ae342d43fb94d03a19b7753bf3f6deee2bbb43",
}

IMAGE_SHA256 = "8a4aea91b809423561ffd7cb9bf6f651dd01c1952815e0fce467ce860d944312"
IMAGE_BYTES = 59374080
NEW_DTB_SHA256 = (
    "d7d8a7da7a3fc68b37faceda0fd7c7f506fbbd17b7a510c15cb978b9160acf1b"
)
NEW_DTB_BYTES = 116962
RUNTIME_DTB_SHA256 = (
    "d7d8a7da7a3fc68b37faceda0fd7c7f506fbbd17b7a510c15cb978b9160acf1b"
)
RUNTIME_DTB_BYTES = 116962

_CHUNK = 1024 * 1024
AUDIT_REPORT_REQUIRED_KEYS = (
    "schema",
    "trial_id",
    "passed",
    "read_only",
    "accepted_token_written",
    "high_voltage_accessed",
    "boot_id",
    "version",
    "manifest_sha256",
    "service_runlevel",
    "watchdog",
    "carrier_readback",
    "eud_route",
    "ncm",
    "typec",
    "tcpm",
    "native",
    "mp2650",
    "protection",
    "apsd_adc",
    "kernel_log",
    "fixed_5v_only",
    "accepted",
)


class TrialError(RuntimeError):
    """A fail-closed trial condition."""


def runtime_kernel_version_matches(actual: object, expected: str) -> bool:
    """Accept the exact UTS version or a complete /proc/version suffix."""
    if not isinstance(actual, str) or not isinstance(expected, str) or not expected:
        return False
    if actual == expected:
        return True
    prefix = "Linux version "
    suffix = " " + expected
    return (
        actual.startswith(prefix)
        and len(actual) > len(prefix) + len(suffix)
        and actual.endswith(suffix)
    )


def module_vermagic(path: Path) -> str:
    """Read vermagic from the .modinfo section of a little-endian ELF64 module."""
    raw = Path(path).read_bytes()
    if len(raw) < 64 or raw[:4] != b"\x7fELF" or raw[4:6] != b"\x02\x01":
        raise TrialError(f"module is not little-endian ELF64: {path}")
    try:
        section_offset = struct.unpack_from("<Q", raw, 40)[0]
        section_size, section_count, string_index = struct.unpack_from(
            "<HHH", raw, 58
        )
        if section_size < 64 or section_count == 0 or string_index >= section_count:
            raise TrialError(f"module has an invalid section table: {path}")
        sections = [
            struct.unpack_from(
                "<IIQQQQIIQQ",
                raw,
                section_offset + index * section_size,
            )
            for index in range(section_count)
        ]
        string_section = sections[string_index]
        strings = raw[
            string_section[4] : string_section[4] + string_section[5]
        ]
        for section in sections:
            name_offset = section[0]
            name = strings[name_offset:].split(b"\0", 1)[0]
            if name != b".modinfo":
                continue
            start, size = section[4], section[5]
            for field in raw[start : start + size].split(b"\0"):
                if field.startswith(b"vermagic="):
                    return field[len(b"vermagic=") :].decode("ascii")
    except (IndexError, UnicodeDecodeError, struct.error) as error:
        raise TrialError(f"cannot parse module vermagic: {path}") from error
    raise TrialError(f"module vermagic is missing: {path}")


def sha256_file(path: Path, chunk_size: int = _CHUNK) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while True:
            block = stream.read(chunk_size)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def require_regular(
    path: Path,
    *,
    require_root: bool = False,
    max_mode: int = 0o755,
) -> os.stat_result:
    info = Path(path).lstat()
    if not stat.S_ISREG(info.st_mode):
        raise TrialError(f"not a regular file: {path}")
    if require_root and info.st_uid != 0:
        raise TrialError(f"not owned by root: {path}")
    if os.name != "nt":
        if info.st_mode & 0o022:
            raise TrialError(f"writable by group/other: {path}")
        if stat.S_IMODE(info.st_mode) & ~max_mode:
            raise TrialError(f"unexpected mode: {path}")
    return info


def inspect_service_runlevel(
    target_root: Path = Path("/"),
    *,
    require_root: bool = False,
) -> dict:
    """Read the fixed OpenRC default-runlevel link without changing it."""
    target_root = Path(target_root)
    path = (
        RUNLEVEL_PATH
        if target_root == Path("/")
        else target_root / RUNLEVEL_PATH.relative_to("/")
    )
    parent_info = path.parent.lstat()
    if not stat.S_ISDIR(parent_info.st_mode):
        raise TrialError(f"runlevel directory is not a real directory: {path.parent}")
    if require_root and parent_info.st_uid != 0:
        raise TrialError(f"runlevel directory is not owned by root: {path.parent}")
    if os.name != "nt" and parent_info.st_mode & 0o022:
        raise TrialError(f"runlevel directory is writable by group/other: {path.parent}")
    try:
        info = path.lstat()
    except FileNotFoundError:
        return {
            "target": RUNLEVEL_PATH.as_posix(),
            "before": "missing",
            "added": False,
            "link_target": None,
            "verified": True,
        }
    if not stat.S_ISLNK(info.st_mode):
        raise TrialError(f"runlevel path must be missing or a symlink: {path}")
    link_target = os.readlink(path)
    if link_target != SERVICE_PATH.as_posix():
        raise TrialError(
            f"runlevel link has unexpected target: {link_target!r}"
        )
    return {
        "target": RUNLEVEL_PATH.as_posix(),
        "before": "enabled",
        "added": False,
        "link_target": link_target,
        "verified": True,
    }


def validate_service_runlevel(value: object) -> dict:
    """Validate a runlevel receipt so rollback can never guess at a path."""
    if not isinstance(value, dict):
        raise TrialError("service runlevel receipt missing")
    if value.get("target") != RUNLEVEL_PATH.as_posix():
        raise TrialError("service runlevel receipt has an unexpected path")
    before = value.get("before")
    added = value.get("added")
    link_target = value.get("link_target")
    if before not in {"missing", "enabled"}:
        raise TrialError("service runlevel receipt has an invalid prior state")
    if type(added) is not bool or value.get("verified") is not True:
        raise TrialError("service runlevel receipt is not verified")
    if before == "enabled":
        if added or link_target != SERVICE_PATH.as_posix():
            raise TrialError("pre-existing runlevel link receipt is inconsistent")
    elif added:
        if link_target != SERVICE_PATH.as_posix():
            raise TrialError("new runlevel link receipt is inconsistent")
    elif link_target is not None:
        raise TrialError("missing runlevel link receipt has a target")
    return value


def restore_service_runlevel(
    target_root: Path,
    value: object,
    *,
    fsync_directory,
) -> dict:
    """Restore exactly the recorded runlevel state without touching foreign links."""
    record = validate_service_runlevel(value)
    target_root = Path(target_root)
    path = (
        RUNLEVEL_PATH
        if target_root == Path("/")
        else target_root / RUNLEVEL_PATH.relative_to("/")
    )
    current = inspect_service_runlevel(target_root)
    if not record["added"]:
        expected = record["before"]
        if current["before"] != expected:
            raise TrialError(
                f"runlevel changed before rollback: expected {expected}, "
                f"found {current['before']}"
            )
        return {
            **record,
            "removed": False,
            "verified": current["before"] == expected,
        }
    if record["before"] != "missing" or current["before"] != "enabled":
        raise TrialError("new runlevel link is not present for exact rollback")
    path.unlink()
    fsync_directory(path.parent)
    after = inspect_service_runlevel(target_root)
    if after["before"] != "missing":
        raise TrialError("runlevel link removal was not durable")
    return {
        **record,
        "removed": True,
        "verified": True,
    }


def read_json(path: Path) -> dict:
    raw = Path(path).read_bytes()
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise TrialError(f"JSON object required: {path}")
    return value


def atomic_write(path: Path, raw: bytes, mode: int = 0o600) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    tmp = path.with_name(path.name + ".next")
    if tmp.exists() or tmp.is_symlink():
        raise TrialError(f"stale temporary file: {tmp}")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(tmp, flags, mode)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
            os.fchmod(stream.fileno(), mode)
        os.replace(tmp, path)
    except BaseException:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass
        raise
    try:
        dfd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    except OSError:
        return
    try:
        os.fsync(dfd)
    finally:
        os.close(dfd)


def copy_verified(
    source: Path,
    destination: Path,
    *,
    expected_sha256: str | None = None,
    expected_bytes: int | None = None,
    mode: int = 0o600,
) -> dict:
    """Copy one file to a new private path and verify the written bytes."""
    source = Path(source)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_NOFOLLOW", 0)
    digest = hashlib.sha256()
    total = 0
    remaining = expected_bytes
    fd = os.open(destination, flags, mode)
    try:
        with os.fdopen(fd, "wb") as out, source.open("rb") as stream:
            while True:
                amount = _CHUNK if remaining is None else min(_CHUNK, remaining)
                if amount == 0:
                    break
                block = stream.read(amount)
                if not block:
                    break
                out.write(block)
                digest.update(block)
                total += len(block)
                if remaining is not None:
                    remaining -= len(block)
            out.flush()
            os.fsync(out.fileno())
            os.fchmod(out.fileno(), mode)
    except BaseException:
        try:
            destination.unlink()
        except FileNotFoundError:
            pass
        raise
    actual = digest.hexdigest()
    if expected_sha256 is not None and actual != expected_sha256:
        destination.unlink()
        raise TrialError(f"copy hash mismatch: {destination}")
    if expected_bytes is not None and total != expected_bytes:
        destination.unlink()
        raise TrialError(f"copy size mismatch: {destination}")
    return {"path": str(destination), "sha256": actual, "bytes": total}


def active_value(value: str) -> str:
    selected = re.findall(r"\[([^\]]+)\]", value)
    if len(selected) == 1:
        return selected[0]
    return value.strip()


def parse_key_values(text: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for word in text.split():
        if "=" not in word:
            continue
        key, value = word.split("=", 1)
        try:
            result[key] = int(value, 0)
        except ValueError as error:
            raise TrialError(f"invalid key/value: {word}") from error
    return result


def manifest_sha256(path: Path) -> str:
    return sha256_file(Path(path))


def canonical_json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def validate_complete_passed_audit_report(
    report: object,
    *,
    boot_id: str,
    manifest_sha256_value: str,
) -> dict:
    """Accept only a complete, read-only report for this exact boot/manifest."""
    if not isinstance(report, dict):
        raise TrialError("audit report must be a JSON object")
    missing = [key for key in AUDIT_REPORT_REQUIRED_KEYS if key not in report]
    if missing:
        raise TrialError(f"audit report is incomplete: missing {missing}")
    if report.get("schema") != 1 or report.get("trial_id") != TRIAL_ID:
        raise TrialError("unexpected audit report schema or trial id")
    if report.get("passed") is not True:
        raise TrialError("audit report did not pass")
    if report.get("read_only") is not True:
        raise TrialError("audit report is not read-only")
    if report.get("accepted_token_written") is not False:
        raise TrialError("audit report must not write the acceptance token")
    if report.get("high_voltage_accessed") is not False:
        raise TrialError("audit report accessed high voltage")
    if report.get("boot_id") != boot_id:
        raise TrialError("audit report belongs to a different boot")
    if report.get("manifest_sha256") != manifest_sha256_value:
        raise TrialError("audit report was produced for another manifest")
    if report.get("fixed_5v_only") is not True or report.get("accepted") is not False:
        raise TrialError("audit report does not prove a fresh fixed-5V acceptance")
    if "error" in report or "traceback" in report:
        raise TrialError("passed audit report contains failure evidence")
    return report


def bool_field(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise TrialError(f"{name} must be a JSON boolean")
    return value

