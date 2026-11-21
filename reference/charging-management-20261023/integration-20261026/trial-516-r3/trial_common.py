"""Shared constants and filesystem primitives for the #516 trial.

This module is intentionally free of device discovery and command execution so
the guard, stage helper, and local control tests can all use the same rules.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from pathlib import Path


TRIAL_ID = "charging-integration-516-20261026-07"
TOKEN = "cfc12f97f14cb97aa8819405bd412198ce214d3a098d5615a2f0975aa8fb5a7c"
VERSION = "#516 SMP PREEMPT Mon Oct 26 19:29:22 CST 2026"
RELEASE = "7.3.0-rc6-rmx1931-samurai-k363+"
WATCH_SECONDS = 300
EXPECTED_TAINTED = 4096

DEVICE_ROOT = Path(
    "/root/charging-management-20261023/charging-integration-trial-20261026-07"
)
GUARD_PATH = Path("/usr/lib/samurai-charging/trial_guard.py")
COMMON_PATH = Path("/usr/lib/samurai-charging/trial_common.py")
SERVICE_PATH = Path("/etc/init.d/samurai-charging")
RUNLEVEL_DIR = Path("/etc/runlevels/default")
RUNLEVEL_PATH = RUNLEVEL_DIR / "samurai-charging"
RUNLEVEL_ADD_ARGV = ("/sbin/rc-update", "add", "samurai-charging", "default")
MAIN_MANIFEST_PATH = Path("/usr/share/samurai-charging/manifest.json")
MANIFEST_PATH = Path("/usr/share/samurai-charging/trial-manifest.json")
MAIN_MANIFEST_SHA256 = (
    "8b402e1c37ca390ec2be4949738badb670e9b5c54cbcf6941c895935ed90bc0a"
)

MODULE_NAME = "samurai-mp2650"
MODULE_SOURCE = "modules/samurai-mp2650.ko"
MODULE_PATH = Path(
    "/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/"
    "samurai-mp2650.ko"
)
MODULE_MODE = 0o644
MODULE_OLD_SHA256 = (
    "bef4dba73e1244fec4c89f2d5b47ac6b1483384c1f64aa1d589de792d2e97d6f"
)
MODULE_OLD_BYTES = 156784
MODULE_NEW_SHA256 = (
    "04da6a7bf492e44d6afa533816e662d54b5a5f0391f4fe0e5e6e7f8555cedf69"
)
MODULE_NEW_BYTES = 164360

PARTITION_BYTES = {
    "boot": 100663296,
    "logdump": 67108864,
}

NEW_CARRIER_SHA256 = {
    "boot": "3e64f76801ac26d8ca0654960fc15dd10e627deb13c0831a7392c9846b1ec055",
    "logdump": "4a47fa17ceb51fc0a689726556ca4e9b6d6752902d54f3874c13e5935aa28016",
}
OLD_CARRIER_SHA256 = {
    "boot": "5c8d23d4d5e834593dd3a24537044af8b57e2df53ed3a91fb7880ad7541f8311",
    "logdump": "b29ea41a7a076555f5f6848c9f343dbd8fb0f9271adbd4d3acd4fff9d092b0ff",
}

IMAGE_SHA256 = "812f1633e5f92c6ff5e99440a27e03f57d790db6728aee50930719ca5531eddd"
IMAGE_BYTES = 59374080
NEW_DTB_SHA256 = (
    "b989d5f04dcb3785436db5d5c0ac6524509f0b785df432ca38d658452618da87"
)
NEW_DTB_BYTES = 116012
RUNTIME_DTB_SHA256 = (
    "b989d5f04dcb3785436db5d5c0ac6524509f0b785df432ca38d658452618da87"
)
RUNTIME_DTB_BYTES = 116012

_CHUNK = 1024 * 1024


class TrialError(RuntimeError):
    """A fail-closed trial condition."""


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
            "target": str(RUNLEVEL_PATH),
            "before": "missing",
            "added": False,
            "link_target": None,
            "verified": True,
        }
    if not stat.S_ISLNK(info.st_mode):
        raise TrialError(f"runlevel path must be missing or a symlink: {path}")
    link_target = os.readlink(path)
    if link_target != str(SERVICE_PATH):
        raise TrialError(
            f"runlevel link has unexpected target: {link_target!r}"
        )
    return {
        "target": str(RUNLEVEL_PATH),
        "before": "enabled",
        "added": False,
        "link_target": link_target,
        "verified": True,
    }


def validate_service_runlevel(value: object) -> dict:
    """Validate a runlevel receipt so rollback can never guess at a path."""
    if not isinstance(value, dict):
        raise TrialError("service runlevel receipt missing")
    if value.get("target") != str(RUNLEVEL_PATH):
        raise TrialError("service runlevel receipt has an unexpected path")
    before = value.get("before")
    added = value.get("added")
    link_target = value.get("link_target")
    if before not in {"missing", "enabled"}:
        raise TrialError("service runlevel receipt has an invalid prior state")
    if type(added) is not bool or value.get("verified") is not True:
        raise TrialError("service runlevel receipt is not verified")
    if before == "enabled":
        if added or link_target != str(SERVICE_PATH):
            raise TrialError("pre-existing runlevel link receipt is inconsistent")
    elif added:
        if link_target != str(SERVICE_PATH):
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


def bool_field(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise TrialError(f"{name} must be a JSON boolean")
    return value

