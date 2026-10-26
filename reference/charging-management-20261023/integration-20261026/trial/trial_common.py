"""Shared constants and filesystem primitives for the #513 trial.

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


TRIAL_ID = "charging-integration-513-20261026-03"
TOKEN = "6f8755dfd4f5238eb4ad7003e6ddbe8ebd93c8404c64972d7251236933ab9756"
VERSION = "#513 SMP PREEMPT Mon Oct 26 16:51:54 CST 2026"
RELEASE = "7.3.0-rc6-rmx1931-samurai-k363+"
WATCH_SECONDS = 300
EXPECTED_TAINTED = 4096

DEVICE_ROOT = Path(
    "/root/charging-management-20261023/charging-integration-trial-20261026-03"
)
GUARD_PATH = Path("/usr/lib/samurai-charging/trial_guard.py")
COMMON_PATH = Path("/usr/lib/samurai-charging/trial_common.py")
SERVICE_PATH = Path("/etc/init.d/samurai-charging")
MAIN_MANIFEST_PATH = Path("/usr/share/samurai-charging/manifest.json")
MANIFEST_PATH = Path("/usr/share/samurai-charging/trial-manifest.json")
MAIN_MANIFEST_SHA256 = (
    "8b402e1c37ca390ec2be4949738badb670e9b5c54cbcf6941c895935ed90bc0a"
)

PARTITION_BYTES = {
    "boot": 100663296,
    "logdump": 67108864,
}

NEW_CARRIER_SHA256 = {
    "boot": "8af84ca536c9d4e1f09d7395adb303ba6f2ed6fa9138adef074df95e68e56680",
    "logdump": "074518a70b23d8fe7380355af174a5c42da0fdba4e1f19f95f0bf1c77e45df58",
}
OLD_CARRIER_SHA256 = {
    "boot": "5c8d23d4d5e834593dd3a24537044af8b57e2df53ed3a91fb7880ad7541f8311",
    "logdump": "b29ea41a7a076555f5f6848c9f343dbd8fb0f9271adbd4d3acd4fff9d092b0ff",
}

IMAGE_SHA256 = "3893a1c29a143325e7067e1d88fdf539332ae7ec11ac83fea263a86956d372b5"
IMAGE_BYTES = 59374080
NEW_DTB_SHA256 = "9aa3e6fce7833f294a2dd7dc9b8f9d4fc95f3627d0c2386ba2ce183bc4316cd6"
NEW_DTB_BYTES = 116966

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

