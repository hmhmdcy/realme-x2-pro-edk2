#!/usr/bin/env python3
"""Prepare, but do not execute, the next full-boot RMX1931 charging trial.

This helper is intentionally offline.  It only reads local build/package
artifacts and writes a new trial directory when ``--materialize`` is supplied
explicitly.  The default mode is a deterministic plan with no filesystem
writes.  It never invokes SSH, adb, fastboot, a device wrapper, or a reboot.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import sys
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent
SOURCE_TRIAL = ROOT / "trial-517-wake-r1"
TARGET_TRIAL = ROOT / "trial-517-r8-status-precharge"
ARTIFACT_ROOT = Path(r"E:\edk2-samurai-out\charging-management-20261023")

SOURCE_MANIFEST_SHA256 = (
    "ab69570b74e64715267b0aec62c00660c0c651856416a375452b5d7351a8f147"
)
SOURCE_TRIAL_ID = "charging-integration-517-wake-r1-20261027"
SOURCE_TOKEN = "4c8de94225eea9c0d2dea218177ca7192343bf6c9cff43cd4f290b0be89f12d8"
SOURCE_KERNEL_VERSION = "#517 SMP PREEMPT Tue Oct 27 00:17:40 CST 2026"
SOURCE_RELEASE = "7.3.0-rc6-rmx1931-samurai-k363+"

CURRENT_BOOT = (
    ARTIFACT_ROOT
    / "charging-integration-20261027-boot-private-01"
    / "boot-eud-off-route-private-r7.img"
)
CURRENT_BOOT_SHA256 = (
    "13c98860646fa80241a0a042e17781fceb7873f13263c69433839fd11ab9f756"
)
CURRENT_IMAGE_MANIFEST_PATH = Path(
    "/home/cy122/charging-management-20261023/"
    "charging-integration-20261026-01/build-r7/Image-r7-k517.img"
)
CURRENT_IMAGE_HOST_PATH = Path(
    r"\\wsl.localhost\Ubuntu\home\cy122\charging-management-20261023"
    r"\charging-integration-20261026-01\build-r7\Image-r7-k517.img"
)
CURRENT_IMAGE_SHA256 = (
    "6e45cbb780b7de690f714a17b54524369b630eccff8ee773acbbb38a59f90f2f"
)
CURRENT_IMAGE_BYTES = 59_374_080
CURRENT_PRIMARY_MODULE_SHA256 = (
    "04da6a7bf492e44d6afa533816e662d54b5a5f0391f4fe0e5e6e7f8555cedf69"
)
CURRENT_PRIMARY_MODULE_BYTES = 164_360

CURRENT_LOGDUMP = (
    ARTIFACT_ROOT
    / "charging-integration-20261027-fat-private-01"
    / "logdump-tcpm-sink507-r2-private.img"
)
CURRENT_LOGDUMP_SHA256 = (
    "d884075a04d00112c95d0d3215ae342d43fb94d03a19b7753bf3f6deee2bbb43"
)
LOGDUMP_BYTES = 67_108_864

DTB = (
    ARTIFACT_ROOT
    / "charging-integration-20261026-dtb-private-02"
    / "samurai-eud-off-route-okay.dtb"
)
DTB_SHA256 = "d7d8a7da7a3fc68b37faceda0fd7c7f506fbbd17b7a510c15cb978b9160acf1b"
DTB_BYTES = 116_962

USB_MODULE_DEFAULT = SOURCE_TRIAL / "modules/samurai-usb-input.ko"
USB_MODULE_NEW_SHA256 = (
    "22604106772b89758ea745531e99dd70a6ab696b7740705107a767599e9a6529"
)
USB_MODULE_NEW_BYTES = 91_896
USB_MODULE_K518_SHA256 = (
    "37d74184e3e6f71dfc0abccd77f63dba0715550e54fd492df4ac0db59237947f"
)
USB_MODULE_K518_BYTES = 91_888
USB_MODULE_OLD_SHA256 = (
    "161bcc3376864e6f867aa5cc0371b5ab61ba9d716108aad0f45e6c765d378f86"
)
USB_MODULE_OLD_BYTES = 26_128

PLANNED_TRIAL_ID = "charging-integration-r8-status-precharge-20261027"
PLANNED_DEVICE_ROOT = (
    "/root/charging-management-20261023/trial-517-r8-status-precharge"
)
BQ_SYMBOL = "bq27xxx_battery_set_status_override"
PRIMARY_MODULE_NAME = "samurai-mp2650"
USB_MODULE_NAME = "samurai-usb-input"
WATCH_SECONDS = 300

SOURCE_FILES_REQUIRED = (
    "manifest.json",
    "README.md",
    "COMMANDS.md",
    "trial_common.py",
    "trial_stage.py",
    "trial_guard.py",
    "postboot_audit.py",
    "trial_autoaudit.py",
    "fastboot_operator.ps1",
    "service/samurai-charging",
)

SKIP_NAMES = {
    "__pycache__",
    "manifest.json",
    "package-result.json",
    "SHA256SUMS",
    "SHA256SUMS.verify.txt",
    "test-results.json",
    "test-results-linux.json",
    "test-results-r8-preview.json",
    "test-run-linux.log",
    "test-run-windows.log",
}


class PreparationError(RuntimeError):
    """A deterministic package-preparation precondition failed."""


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    ).encode("utf-8")


def read_json(path: Path) -> dict:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise PreparationError(f"JSON object required: {path}")
    return value


def require_regular(path: Path, label: str) -> Path:
    path = Path(path)
    try:
        info = path.stat()
    except FileNotFoundError as error:
        raise PreparationError(f"{label} is missing: {path}") from error
    if not stat.S_ISREG(info.st_mode):
        raise PreparationError(f"{label} is not a regular file: {path}")
    return path


def require_hex(value: str, label: str) -> str:
    value = value.strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", value):
        raise PreparationError(f"{label} must be a lowercase SHA-256 hex digest")
    return value


def pin_file(
    path: Path,
    expected_sha256: str,
    *,
    label: str,
    expected_bytes: int | None = None,
) -> dict:
    path = require_regular(path, label)
    digest = require_hex(expected_sha256, f"{label} SHA-256")
    actual = sha256_file(path)
    if actual != digest:
        raise PreparationError(
            f"{label} SHA-256 mismatch: expected {digest}, found {actual}"
        )
    size = path.stat().st_size
    if expected_bytes is not None and size != expected_bytes:
        raise PreparationError(
            f"{label} size mismatch: expected {expected_bytes}, found {size}"
        )
    return {"path": str(path), "sha256": actual, "bytes": size}


def file_contains(path: Path, needle: bytes) -> bool:
    if not needle:
        raise PreparationError("empty binary search needle")
    overlap = max(0, len(needle) - 1)
    tail = b""
    with Path(path).open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            window = tail + chunk
            if needle in window:
                return True
            tail = window[-overlap:] if overlap else b""
    return False


def normalize_comparable_path(value: str | Path) -> str:
    text = str(value).strip().replace("\\", "/")
    if text.startswith("/mnt/") and len(text) > 6 and text[6] == "/":
        text = text[5].upper() + ":" + text[6:]
    while "//" in text:
        text = text.replace("//", "/")
    return text.rstrip("/").lower()


def artifact_suffix(path: Path) -> str:
    text = str(path).replace("\\", "/")
    marker = "/charging-management-20261023/"
    index = text.find(marker)
    if index < 0:
        raise PreparationError(
            f"artifact path is outside the charging-management artifact root: {path}"
        )
    return text[index + 1 :]


def _require_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise PreparationError(f"{label} must be a non-empty string")
    return value


def _require_true(value: object, label: str) -> None:
    if value is not True:
        raise PreparationError(f"{label} must be true")


def _find_fat_pins(receipt: dict) -> tuple[dict, dict, dict | None]:
    image = receipt.get("unchanged_image") or receipt.get("Image507_R2")
    if not isinstance(image, dict):
        raise PreparationError("FAT receipt has no Image pin")

    candidate_fat = receipt.get("candidate_fat")
    if isinstance(candidate_fat, dict):
        logdump = candidate_fat
        dtb = receipt.get("candidate_dtb")
        if receipt.get("fat_integrity", {}).get("only_dtb_file_changed") is not True:
            raise PreparationError("FAT receipt must prove only samurai.dtb changed")
        if candidate_fat.get("fsck", {}).get("returncode") != 0:
            raise PreparationError("FAT receipt fsck did not pass")
        if not isinstance(dtb, dict):
            raise PreparationError("FAT receipt has no candidate DTB pin")
        return image, logdump, dtb

    logdump = receipt.get("candidate")
    if not isinstance(logdump, dict):
        raise PreparationError("FAT receipt has no logdump candidate pin")
    if receipt.get("Image_readback_exact") is not True:
        raise PreparationError("FAT receipt must prove exact Image readback")
    if receipt.get("only_Image_file_changed") is not True:
        raise PreparationError("FAT receipt must prove only the Image changed")
    if receipt.get("fsck_readonly_passed") is not True:
        raise PreparationError("FAT receipt must prove a readonly fsck pass")
    return image, logdump, None


def inspect_fat_receipt(
    path: Path,
    *,
    image_sha256: str,
    image_bytes: int,
    logdump_sha256: str,
    logdump_bytes: int,
    dtb_sha256: str,
    dtb_bytes: int,
) -> dict:
    path = require_regular(path, "FAT receipt")
    receipt = read_json(path)
    _require_true(receipt.get("passed"), "FAT receipt passed")
    image, logdump, dtb = _find_fat_pins(receipt)
    if image.get("sha256") != image_sha256 or image.get("bytes") != image_bytes:
        raise PreparationError("FAT receipt Image pin does not match the new Image")
    if (
        logdump.get("sha256") != logdump_sha256
        or logdump.get("bytes") != logdump_bytes
    ):
        raise PreparationError("FAT receipt logdump pin does not match the new FAT")
    if dtb is not None and (
        dtb.get("sha256") != dtb_sha256 or dtb.get("bytes") != dtb_bytes
    ):
        raise PreparationError("FAT receipt DTB pin does not match the runtime DTB")
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "image_sha256": image_sha256,
        "logdump_sha256": logdump_sha256,
        "dtb_sha256": dtb_sha256,
        "only_expected_fat_file_changed": True,
    }


def inspect_boot_receipt(
    path: Path,
    *,
    boot_path: Path,
    boot_sha256: str,
    image_sha256: str,
    dtb_sha256: str,
    allow_identical_boot: bool,
) -> dict:
    path = require_regular(path, "boot package receipt")
    receipt = read_json(path)
    _require_true(receipt.get("passed"), "boot package receipt passed")
    _require_true(
        receipt.get("written_boot_fully_reparsed"),
        "boot package receipt fully reparsed output",
    )
    _require_true(
        receipt.get("geometry_passed"),
        "boot package receipt geometry",
    )
    _require_true(
        receipt.get("no_device_or_deployment"),
        "boot package receipt offline scope",
    )
    if receipt.get("boot_sha256") != boot_sha256:
        raise PreparationError("boot package receipt boot hash mismatch")
    if receipt.get("fat_Image_sha256") != image_sha256:
        raise PreparationError("boot package receipt Image hash mismatch")
    if receipt.get("native_DTB_sha256") != dtb_sha256:
        raise PreparationError("boot package receipt DTB hash mismatch")
    identical_to_rollback = boot_sha256 == CURRENT_BOOT_SHA256
    if identical_to_rollback:
        if not allow_identical_boot:
            raise PreparationError(
                "the new boot equals the current rollback boot; pass "
                "--allow-identical-boot only for a FAT/Image-only update"
            )
        for field in (
            "only_embedded_DTB_payload_changed",
            "other_main_FFS_exact",
            "compact_SEC_exact",
            "shim_exact",
            "compat_exact",
            "ramdisk_exact",
            "absolute_tail_exact",
            "written_boot_fully_reparsed",
            "no_device_or_deployment",
        ):
            _require_true(
                receipt.get(field),
                f"identical boot receipt {field}",
            )
    receipt_boot = _require_string(receipt.get("boot_path"), "boot receipt boot_path")
    if normalize_comparable_path(receipt_boot) != normalize_comparable_path(boot_path):
        raise PreparationError("boot package receipt boot_path mismatch")
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "boot_path": str(boot_path),
        "boot_sha256": boot_sha256,
        "image_sha256": image_sha256,
        "dtb_sha256": dtb_sha256,
        "identical_to_rollback": identical_to_rollback,
    }


def inspect_symvers(path: Path, symbol: str) -> dict:
    path = require_regular(path, "Module.symvers")
    rows = []
    for line in path.read_text(encoding="utf-8", errors="strict").splitlines():
        columns = line.split()
        if len(columns) >= 4 and columns[1] == symbol:
            rows.append(
                {
                    "address": columns[0],
                    "symbol": columns[1],
                    "owner": columns[2],
                    "export": columns[3],
                    "line_sha256": sha256_bytes(line.encode("utf-8")),
                }
            )
    if len(rows) != 1:
        raise PreparationError(
            f"Module.symvers must contain exactly one {symbol} export; found {len(rows)}"
        )
    row = rows[0]
    if row["owner"] != "vmlinux":
        raise PreparationError(f"{symbol} must be exported by built-in vmlinux")
    if row["export"] != "EXPORT_SYMBOL_GPL":
        raise PreparationError(f"{symbol} must use EXPORT_SYMBOL_GPL")
    return {
        **row,
        "module_symvers_path": str(path),
        "module_symvers_sha256": sha256_file(path),
        "module_symvers_bytes": path.stat().st_size,
    }


def inspect_build(
    *,
    build_root: Path,
    image_path: Path,
    image_file: Path,
    image_sha256: str,
    image_bytes: int,
    kernel_version: str,
    kernel_build_label: str,
    kernel_release: str,
) -> dict:
    try:
        build_root = build_root.resolve(strict=True)
    except OSError as error:
        raise PreparationError(f"build root is unavailable: {build_root}") from error
    if not build_root.is_dir():
        raise PreparationError(f"build root is not a directory: {build_root}")

    label, separator, suffix = kernel_version.partition(" ")
    if not separator or not re.fullmatch(r"#\d+", label):
        raise PreparationError(
            "kernel version must start with a build label such as '#518 '"
        )
    if kernel_build_label != label:
        raise PreparationError(
            f"kernel build label mismatch: expected {label}, found {kernel_build_label}"
        )

    built_image = require_regular(
        build_root / "arch/arm64/boot/Image", "built arch/arm64/boot/Image"
    )
    built_image_pin = pin_file(
        built_image,
        image_sha256,
        expected_bytes=image_bytes,
        label="built Image",
    )
    try:
        image_file = image_file.resolve(strict=True)
    except OSError as error:
        raise PreparationError(f"selected Image is unavailable: {image_file}") from error
    selected_image_pin = pin_file(
        image_file,
        image_sha256,
        expected_bytes=image_bytes,
        label="selected Image",
    )
    if not image_file.is_relative_to(build_root):
        raise PreparationError(
            "selected Image must be inside the same build root as vmlinux/Module.symvers"
        )

    release_file = build_root / "include/config/kernel.release"
    release_file = require_regular(release_file, "build kernel.release")
    build_release = release_file.read_text(encoding="utf-8").strip()
    if kernel_release not in {build_release, build_release + "+"}:
        raise PreparationError(
            f"runtime kernel release {kernel_release!r} does not match "
            f"build release {build_release!r}"
        )

    vmlinux = require_regular(build_root / "vmlinux", "build vmlinux")
    system_map = require_regular(build_root / "System.map", "build System.map")
    if not file_contains(vmlinux, kernel_version.encode("utf-8")):
        raise PreparationError(
            "the exact kernel build label is not embedded in the selected vmlinux"
        )
    if not file_contains(vmlinux, f"Linux version {kernel_release}".encode("utf-8")):
        raise PreparationError(
            "the selected vmlinux does not contain the expected Linux release"
        )

    symvers = build_root / "Module.symvers"
    export = inspect_symvers(symvers, BQ_SYMBOL)
    return {
        "build_root": str(build_root),
        "built_image": built_image_pin,
        "selected_image": selected_image_pin,
        "image_manifest_path": str(image_path),
        "kernel_release": kernel_release,
        "kernel_release_base": build_release,
        "kernel_build_label": kernel_build_label,
        "kernel_version": kernel_version,
        "kernel_version_suffix": suffix,
        "vmlinux": {
            "path": str(vmlinux),
            "sha256": sha256_file(vmlinux),
            "bytes": vmlinux.stat().st_size,
            "contains_exact_kernel_version": True,
        },
        "system_map": {
            "path": str(system_map),
            "sha256": sha256_file(system_map),
            "bytes": system_map.stat().st_size,
        },
        "bq27xxx_export": export,
    }


def inspect_module(
    path: Path,
    *,
    expected_sha256: str,
    kernel_release: str,
    module_name: str,
    label: str,
    expected_bytes: int | None = None,
) -> dict:
    pin = pin_file(
        path,
        expected_sha256,
        expected_bytes=expected_bytes,
        label=label,
    )
    path = Path(path)
    if not file_contains(path, f"vermagic={kernel_release} ".encode("utf-8")):
        raise PreparationError(f"{label} vermagic does not match {kernel_release}")
    if not file_contains(path, f"name={module_name}".encode("utf-8")):
        raise PreparationError(f"{label} module name is not {module_name}")
    return pin


def derive_token(
    *,
    trial_id: str,
    source_manifest_sha256: str,
    image_sha256: str,
    kernel_version: str,
    kernel_release: str,
    boot_sha256: str,
    primary_module_sha256: str,
    usb_module_sha256: str,
    main_manifest_sha256: str,
) -> str:
    seed = {
        "schema": "samurai-trial-token-v1",
        "trial_id": trial_id,
        "source_manifest_sha256": source_manifest_sha256,
        "image_sha256": image_sha256,
        "kernel_version": kernel_version,
        "kernel_release": kernel_release,
        "boot_sha256": boot_sha256,
        "primary_module_sha256": primary_module_sha256,
        "usb_module_sha256": usb_module_sha256,
        "main_manifest_sha256": main_manifest_sha256,
    }
    return sha256_bytes(canonical_json_bytes(seed))


def _require_cli_inputs(args: argparse.Namespace) -> None:
    required = (
        "image",
        "image_sha256",
        "image_bytes",
        "kernel_version",
        "kernel_release",
        "build_root",
        "boot",
        "boot_sha256",
        "boot_receipt",
        "fat_receipt",
        "logdump",
        "logdump_sha256",
        "mp2650_module",
        "mp2650_module_sha256",
        "usb_module",
        "usb_module_sha256",
        "main_manifest_sha256",
        "dtb",
        "dtb_sha256",
    )
    missing = []
    for name in required:
        value = getattr(args, name)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append("--" + name.replace("_", "-"))
    if missing:
        raise PreparationError("missing required arguments: " + ", ".join(missing))


def build_plan(args: argparse.Namespace) -> dict:
    _require_cli_inputs(args)

    source_manifest = SOURCE_TRIAL / "manifest.json"
    source_manifest_pin = pin_file(
        source_manifest,
        SOURCE_MANIFEST_SHA256,
        label="source wake-r1 manifest",
    )
    for relative in SOURCE_FILES_REQUIRED:
        require_regular(SOURCE_TRIAL / relative, f"source trial file {relative}")

    image_sha256 = require_hex(args.image_sha256, "new Image SHA-256")
    boot_sha256 = require_hex(args.boot_sha256, "new boot SHA-256")
    logdump_sha256 = require_hex(args.logdump_sha256, "new logdump SHA-256")
    primary_sha256 = require_hex(
        args.mp2650_module_sha256, "new samurai-mp2650 SHA-256"
    )
    usb_sha256 = require_hex(args.usb_module_sha256, "wake USB module SHA-256")
    if usb_sha256 not in {USB_MODULE_NEW_SHA256, USB_MODULE_K518_SHA256}:
        raise PreparationError(
            "the r8 scaffold accepts only the verified wake module pins "
            f"{USB_MODULE_NEW_SHA256} or {USB_MODULE_K518_SHA256}"
        )
    old_usb_sha256 = require_hex(args.usb_old_sha256, "old USB module SHA-256")
    main_manifest_sha256 = require_hex(
        args.main_manifest_sha256, "current main manifest SHA-256"
    )
    dtb_sha256 = require_hex(args.dtb_sha256, "runtime DTB SHA-256")
    if image_sha256 == CURRENT_IMAGE_SHA256:
        raise PreparationError("the new Image must differ from the current rollback Image")
    if args.kernel_version == SOURCE_KERNEL_VERSION:
        raise PreparationError("the new kernel build label must differ from #517")
    if primary_sha256 == CURRENT_PRIMARY_MODULE_SHA256:
        raise PreparationError(
            "the new samurai-mp2650 module must differ from the current module"
        )
    if logdump_sha256 == CURRENT_LOGDUMP_SHA256:
        raise PreparationError("the new logdump/FAT must differ from the rollback logdump")

    boot_pin = pin_file(
        args.boot,
        boot_sha256,
        expected_bytes=args.boot_bytes,
        label="new boot carrier",
    )
    if boot_sha256 == CURRENT_BOOT_SHA256 and not args.allow_identical_boot:
        raise PreparationError(
            "the new boot equals the current rollback boot; pass "
            "--allow-identical-boot only for a FAT/Image-only update"
        )
    logdump_pin = pin_file(
        args.logdump,
        logdump_sha256,
        expected_bytes=LOGDUMP_BYTES,
        label="new logdump carrier",
    )
    dtb_pin = pin_file(
        args.dtb,
        dtb_sha256,
        expected_bytes=args.dtb_bytes,
        label="runtime DTB",
    )
    current_boot_pin = pin_file(
        CURRENT_BOOT,
        CURRENT_BOOT_SHA256,
        expected_bytes=args.boot_bytes,
        label="current #517 rollback boot",
    )
    current_logdump_pin = pin_file(
        CURRENT_LOGDUMP,
        CURRENT_LOGDUMP_SHA256,
        expected_bytes=LOGDUMP_BYTES,
        label="current #517 rollback logdump",
    )
    current_image_pin = pin_file(
        CURRENT_IMAGE_HOST_PATH,
        CURRENT_IMAGE_SHA256,
        expected_bytes=CURRENT_IMAGE_BYTES,
        label="current #517 rollback Image",
    )

    image_file = Path(args.image_file or args.image)
    if not image_file.is_file():
        if args.image_file is None:
            raise PreparationError(
                "Image manifest path is not host-readable; pass --image-file "
                "with the corresponding \\\\wsl.localhost path"
            )
        raise PreparationError(f"new Image file is missing: {image_file}")

    build = inspect_build(
        build_root=args.build_root,
        image_path=Path(args.image),
        image_file=image_file,
        image_sha256=image_sha256,
        image_bytes=args.image_bytes,
        kernel_version=args.kernel_version,
        kernel_build_label=args.kernel_build_label,
        kernel_release=args.kernel_release,
    )
    primary_module_pin = inspect_module(
        args.mp2650_module,
        expected_sha256=primary_sha256,
        kernel_release=args.kernel_release,
        module_name="samurai_mp2650",
        label="new samurai-mp2650 module",
    )
    usb_module_pin = inspect_module(
        args.usb_module,
        expected_sha256=usb_sha256,
        kernel_release=args.kernel_release,
        module_name="samurai_usb_input",
        label="wake samurai-usb-input module",
    )
    old_usb_pin = {
        "sha256": old_usb_sha256,
        "bytes": args.usb_old_bytes,
    }
    if old_usb_sha256 == USB_MODULE_OLD_SHA256 and args.usb_old_bytes != 26_128:
        raise PreparationError("old USB module size does not match 161bcc baseline")
    if old_usb_sha256 == USB_MODULE_NEW_SHA256 and args.usb_old_bytes != 91_896:
        raise PreparationError("old USB module size does not match 226041 wake module")
    if old_usb_sha256 == USB_MODULE_K518_SHA256 and args.usb_old_bytes != 91_888:
        raise PreparationError("old USB module size does not match 37d741 wake module")

    fat = inspect_fat_receipt(
        args.fat_receipt,
        image_sha256=image_sha256,
        image_bytes=args.image_bytes,
        logdump_sha256=logdump_sha256,
        logdump_bytes=LOGDUMP_BYTES,
        dtb_sha256=dtb_sha256,
        dtb_bytes=args.dtb_bytes,
    )
    boot_receipt = inspect_boot_receipt(
        args.boot_receipt,
        boot_path=Path(args.boot),
        boot_sha256=boot_sha256,
        image_sha256=image_sha256,
        dtb_sha256=dtb_sha256,
        allow_identical_boot=bool(args.allow_identical_boot),
    )

    token = args.token or derive_token(
        trial_id=args.trial_id,
        source_manifest_sha256=SOURCE_MANIFEST_SHA256,
        image_sha256=image_sha256,
        kernel_version=args.kernel_version,
        kernel_release=args.kernel_release,
        boot_sha256=boot_sha256,
        primary_module_sha256=primary_sha256,
        usb_module_sha256=usb_sha256,
        main_manifest_sha256=main_manifest_sha256,
    )
    token = require_hex(token, "trial token")

    plan = {
        "schema": "samurai-trial-r8-preparation-v1",
        "scope": (
            "offline packaging scaffold only; no phone, SSH, adb, fastboot, "
            "device wrapper, reboot, or charging-hardware access"
        ),
        "default_mode": "plan-only",
        "materialize_requested": bool(args.materialize),
        "source_trial": str(SOURCE_TRIAL),
        "source_manifest": source_manifest_pin,
        "target_trial": str(args.target_trial),
        "target_exists": Path(args.target_trial).exists(),
        "trial_id": args.trial_id,
        "token": token,
        "device_root": args.device_root,
        "stage_mode": "carrier",
        "restart_mode": "bootloader",
        "watch_seconds": WATCH_SECONDS,
        "kernel_version": args.kernel_version,
        "kernel_build_label": args.kernel_build_label,
        "kernel_release": args.kernel_release,
        "image": {
            "path": args.image,
            "host_file": str(build["selected_image"]["path"]),
            "sha256": image_sha256,
            "bytes": args.image_bytes,
        },
        "rollback_baseline": {
            "boot": current_boot_pin,
            "logdump": current_logdump_pin,
            "image": {
                **current_image_pin,
                "manifest_path": str(CURRENT_IMAGE_MANIFEST_PATH),
            },
            "kernel_version": SOURCE_KERNEL_VERSION,
            "kernel_release": SOURCE_RELEASE,
            "primary_module_sha256": CURRENT_PRIMARY_MODULE_SHA256,
            "primary_module_bytes": CURRENT_PRIMARY_MODULE_BYTES,
            "usb_module_sha256": old_usb_sha256,
            "usb_module_bytes": args.usb_old_bytes,
            "main_manifest_sha256": main_manifest_sha256,
        },
        "carriers": {
            "boot": {
                "old": current_boot_pin,
                "new": boot_pin,
            },
            "logdump": {
                "old": current_logdump_pin,
                "new": logdump_pin,
            },
        },
        "runtime_dtb": dtb_pin,
        "fat_receipt": fat,
        "boot_receipt": boot_receipt,
        "boot_identity_unchanged": boot_sha256 == CURRENT_BOOT_SHA256,
        "modules": {
            PRIMARY_MODULE_NAME: {
                "old_sha256": CURRENT_PRIMARY_MODULE_SHA256,
                "old_bytes": CURRENT_PRIMARY_MODULE_BYTES,
                "new": primary_module_pin,
            },
            USB_MODULE_NAME: {
                "old": old_usb_pin,
                "new": usb_module_pin,
            },
        },
        "main_manifest_old_sha256": main_manifest_sha256,
        "bq27xxx_evidence": build["bq27xxx_export"],
        "build_provenance": build,
        "assumptions": {
            "source_is_trial_517_wake_r1": True,
            "current_boot_is_rollback": CURRENT_BOOT_SHA256,
            "current_image_is_rollback": CURRENT_IMAGE_SHA256,
            "current_primary_module_is_rollback": CURRENT_PRIMARY_MODULE_SHA256,
            "current_logdump_is_rollback": CURRENT_LOGDUMP_SHA256,
            "bq_symbol_must_be_builtin_gpl_export": True,
            "full_boot_requires_boot_and_logdump_replacement": True,
            "wake_usb_module_is_not_rebuilt": True,
        },
    }
    return plan


def _replace_required(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count < 1:
        raise PreparationError(f"source no longer contains expected {label}")
    return text.replace(old, new)


def _replace_regex_once(
    text: str, pattern: str, replacement: str, label: str
) -> str:
    updated, count = re.subn(pattern, replacement, text, flags=re.MULTILINE)
    if count != 1:
        raise PreparationError(
            f"expected exactly one {label} match in the source; found {count}"
        )
    return updated


def _replace_string_constant(text: str, name: str, old: str, new: str) -> str:
    pattern = rf'^{re.escape(name)} = "{re.escape(old)}"$'
    return _replace_regex_once(
        text,
        pattern,
        f'{name} = "{new}"',
        f"{name} constant",
    )


def _replace_parenthesized_string_constant(
    text: str, name: str, old: str, new: str
) -> str:
    pattern = (
        rf"^{re.escape(name)} = \(\n"
        rf'    "{re.escape(old)}"\n'
        rf"\)$"
    )
    return _replace_regex_once(
        text,
        pattern,
        f'{name} = (\n    "{new}"\n)',
        f"{name} constant",
    )


def _replace_int_constant(text: str, name: str, old: int, new: int) -> str:
    pattern = rf"^{re.escape(name)} = {old}$"
    return _replace_regex_once(
        text,
        pattern,
        f"{name} = {new}",
        f"{name} integer constant",
    )


def _replace_device_root(text: str, new: str) -> str:
    pattern = r"^DEVICE_ROOT = Path\(\n.*?\n\)$"
    replacement = f'DEVICE_ROOT = Path(\n    "{new}"\n)'
    return _replace_regex_once(text, pattern, replacement, "DEVICE_ROOT block")


def _replace_carrier_block(
    text: str, name: str, boot_hash: str, logdump_hash: str
) -> str:
    pattern = (
        rf"^{re.escape(name)} = \{{\n"
        rf'    "boot": "[0-9a-f]{{64}}",\n'
        rf'    "logdump": "[0-9a-f]{{64}}",\n'
        rf"\}}$"
    )
    replacement = (
        f"{name} = {{\n"
        f'    "boot": "{boot_hash}",\n'
        f'    "logdump": "{logdump_hash}",\n'
        f"}}"
    )
    return _replace_regex_once(text, pattern, replacement, f"{name} block")


def rewrite_trial_common(
    path: Path,
    *,
    trial_id: str,
    token: str,
    kernel_version: str,
    release: str,
    device_root: str,
    main_manifest_sha256: str,
    image_sha256: str,
    image_bytes: int,
    boot_new_sha256: str,
    logdump_new_sha256: str,
    primary_new_sha256: str,
    primary_new_bytes: int,
    usb_old_sha256: str,
    usb_old_bytes: int,
    usb_new_sha256: str,
    usb_new_bytes: int,
) -> None:
    text = path.read_text(encoding="utf-8")
    text = _replace_string_constant(text, "TRIAL_ID", SOURCE_TRIAL_ID, trial_id)
    text = _replace_string_constant(text, "TOKEN", SOURCE_TOKEN, token)
    text = _replace_string_constant(
        text, "VERSION", SOURCE_KERNEL_VERSION, kernel_version
    )
    text = _replace_string_constant(text, "RELEASE", SOURCE_RELEASE, release)
    text = _replace_device_root(text, device_root)
    text = _replace_parenthesized_string_constant(
        text,
        "MAIN_MANIFEST_SHA256",
        "b07f7b4bda544a9631ce682221f1e78601d9b38e78d3151e8ac294b57873272d",
        main_manifest_sha256,
    )
    text = _replace_parenthesized_string_constant(
        text,
        "MODULE_OLD_SHA256",
        CURRENT_PRIMARY_MODULE_SHA256,
        CURRENT_PRIMARY_MODULE_SHA256,
    )
    text = _replace_parenthesized_string_constant(
        text,
        "MODULE_NEW_SHA256",
        CURRENT_PRIMARY_MODULE_SHA256,
        primary_new_sha256,
    )
    text = _replace_int_constant(
        text,
        "MODULE_OLD_BYTES",
        CURRENT_PRIMARY_MODULE_BYTES,
        CURRENT_PRIMARY_MODULE_BYTES,
    )
    text = _replace_int_constant(
        text,
        "MODULE_NEW_BYTES",
        CURRENT_PRIMARY_MODULE_BYTES,
        primary_new_bytes,
    )
    text = _replace_string_constant(
        text, "IMAGE_SHA256", CURRENT_IMAGE_SHA256, image_sha256
    )
    text = _replace_int_constant(
        text, "IMAGE_BYTES", CURRENT_IMAGE_BYTES, image_bytes
    )
    text = _replace_carrier_block(
        text,
        "NEW_CARRIER_SHA256",
        boot_new_sha256,
        logdump_new_sha256,
    )
    text = _replace_carrier_block(
        text,
        "OLD_CARRIER_SHA256",
        CURRENT_BOOT_SHA256,
        CURRENT_LOGDUMP_SHA256,
    )

    if usb_old_sha256 != USB_MODULE_OLD_SHA256:
        text = _replace_required(
            text,
            USB_MODULE_OLD_SHA256,
            usb_old_sha256,
            "old wake USB module hash",
        )
    if usb_old_bytes != USB_MODULE_OLD_BYTES:
        text = _replace_required(
            text,
            f'"old_bytes": {USB_MODULE_OLD_BYTES}',
            f'"old_bytes": {usb_old_bytes}',
            "old wake USB module bytes",
        )
    if usb_new_sha256 != USB_MODULE_NEW_SHA256:
        text = _replace_required(
            text,
            USB_MODULE_NEW_SHA256,
            usb_new_sha256,
            "new wake USB module hash",
        )
    if usb_new_bytes != USB_MODULE_NEW_BYTES:
        text = _replace_required(
            text,
            f'"new_bytes": {USB_MODULE_NEW_BYTES}',
            f'"new_bytes": {usb_new_bytes}',
            "new wake USB module bytes",
        )
    if release != SOURCE_RELEASE:
        text = text.replace(SOURCE_RELEASE, release)
    path.write_text(text, encoding="utf-8", newline="\n")


def rewrite_text_crossrefs(
    root: Path,
    *,
    trial_id: str,
    token: str,
    kernel_version: str,
    release: str,
    device_root: str,
    target_name: str,
) -> None:
    replacements = (
        (SOURCE_TRIAL_ID, trial_id),
        (SOURCE_TOKEN, token),
        (SOURCE_KERNEL_VERSION, kernel_version),
        (SOURCE_RELEASE, release),
        (
            "/root/charging-management-20261023/"
            "charging-integration-517-wake-r1-20261027",
            device_root,
        ),
        ("trial-517-wake-r1", target_name),
    )
    for path in sorted(root.rglob("*")):
        if not path.is_file() or "modules" in path.relative_to(root).parts:
            continue
        if path.name in SKIP_NAMES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        updated = text
        for old, new in replacements:
            if old != new:
                updated = updated.replace(old, new)
        if updated != text or b"\r\n" in path.read_bytes():
            path.write_text(updated, encoding="utf-8", newline="\n")


def build_manifest(
    *,
    source_manifest_path: Path,
    target: Path,
    plan: dict,
    kernel_version: str,
    release: str,
    trial_id: str,
    token: str,
    device_root: str,
    image_path: str,
    image_sha256: str,
    image_bytes: int,
    boot_new_path: Path,
    boot_new_sha256: str,
    logdump_new_path: Path,
    logdump_new_sha256: str,
    dtb_path: Path,
    dtb_sha256: str,
    dtb_bytes: int,
    fat_receipt_path: Path,
    boot_receipt_path: Path,
    primary_module_sha256: str,
    primary_module_bytes: int,
    usb_old_sha256: str,
    usb_old_bytes: int,
    usb_module_sha256: str,
    usb_module_bytes: int,
    main_manifest_sha256: str,
) -> dict:
    manifest = read_json(source_manifest_path)
    manifest.update(
        {
            "trial_id": trial_id,
            "token": token,
            "kernel_version": kernel_version,
            "release": release,
            "device_root": device_root,
            "watch_seconds": WATCH_SECONDS,
            "stage_mode": "carrier",
            "restart_mode": "bootloader",
        }
    )
    manifest["image"] = {
        "path": image_path,
        "sha256": image_sha256,
        "bytes": image_bytes,
        "fat_receipt_path": str(fat_receipt_path),
        "fat_receipt_sha256": sha256_file(fat_receipt_path),
    }
    manifest["carriers"]["boot"] = {
        "bytes": CURRENT_BOOT.stat().st_size,
        "old": CURRENT_BOOT_SHA256,
        "old_path": str(CURRENT_BOOT),
        "new": boot_new_sha256,
        "new_path": str(boot_new_path),
    }
    manifest["carriers"]["logdump"] = {
        "bytes": LOGDUMP_BYTES,
        "old": CURRENT_LOGDUMP_SHA256,
        "old_path": str(CURRENT_LOGDUMP),
        "new": logdump_new_sha256,
        "new_path": str(logdump_new_path),
    }
    manifest["kernel_module"].update(
        {
            "old_sha256": CURRENT_PRIMARY_MODULE_SHA256,
            "old_bytes": CURRENT_PRIMARY_MODULE_BYTES,
            "new_sha256": primary_module_sha256,
            "new_bytes": primary_module_bytes,
        }
    )
    old_release_prefix = f"/lib/modules/{SOURCE_RELEASE}/"
    new_release_prefix = f"/lib/modules/{release}/"
    primary_target = manifest["kernel_module"].get("target")
    if not isinstance(primary_target, str) or old_release_prefix not in primary_target:
        raise PreparationError("source primary module target has an unexpected release")
    manifest["kernel_module"]["target"] = primary_target.replace(
        old_release_prefix, new_release_prefix, 1
    )
    aux = manifest["auxiliary_kernel_modules"]
    if len(aux) != 1 or aux[0].get("name") != USB_MODULE_NAME:
        raise PreparationError("source manifest auxiliary module set changed")
    aux[0].update(
        {
            "old_sha256": usb_old_sha256,
            "old_bytes": usb_old_bytes,
            "new_sha256": usb_module_sha256,
            "new_bytes": usb_module_bytes,
        }
    )
    auxiliary_target = aux[0].get("target")
    if not isinstance(auxiliary_target, str) or old_release_prefix not in auxiliary_target:
        raise PreparationError("source auxiliary module target has an unexpected release")
    aux[0]["target"] = auxiliary_target.replace(
        old_release_prefix, new_release_prefix, 1
    )
    manifest["main_manifest"]["old_sha256"] = main_manifest_sha256
    manifest["dtb"].update(
        {
            "path": str(dtb_path),
            "sha256": dtb_sha256,
            "bytes": dtb_bytes,
            "embedded_in_boot": True,
        }
    )
    manifest["runtime_dtb"].update(
        {
            "path": str(dtb_path),
            "sha256": dtb_sha256,
            "bytes": dtb_bytes,
            "fat_receipt_path": str(fat_receipt_path),
            "fat_receipt_sha256": sha256_file(fat_receipt_path),
        }
    )
    manifest["boot_receipt"].update(
        {
            "path": str(boot_receipt_path),
            "sha256": sha256_file(boot_receipt_path),
            "bytes": boot_receipt_path.stat().st_size,
            "boot_path_suffix": artifact_suffix(boot_new_path),
            "dtb_path_suffix": artifact_suffix(dtb_path),
        }
    )
    manifest["postboot"]["version"] = kernel_version
    manifest["postboot"]["precharge_expectations"] = {
        "reg07_precharge_to_precharge_voltage_mv": 6600,
        "reg03_precharge_current_ma": 480,
        "termination_current_code_preserved": True,
        "evidence_level": "static package metadata; physical low-battery proof pending",
    }
    manifest["image_provenance"] = plan["build_provenance"]
    manifest["rollback_baseline"] = plan["rollback_baseline"]
    manifest["packaging"] = {
        "schema": "samurai-trial-r8-packaging-v1",
        "full_boot": True,
        "replaces_boot_and_logdump": True,
        "boot_identity_unchanged": boot_new_sha256 == CURRENT_BOOT_SHA256,
        "bq27xxx_export_required": BQ_SYMBOL,
        "source_manifest_sha256": SOURCE_MANIFEST_SHA256,
        "source_trial": str(SOURCE_TRIAL),
        "device_io_performed": False,
    }

    for target_path, source, mode in (
        (
            "/etc/init.d/samurai-charging",
            target / "service/samurai-charging",
            0o755,
        ),
        (
            "/usr/lib/samurai-charging/postboot_audit.py",
            target / "postboot_audit.py",
            0o644,
        ),
        (
            "/usr/lib/samurai-charging/trial_autoaudit.py",
            target / "trial_autoaudit.py",
            0o755,
        ),
        (
            "/usr/lib/samurai-charging/trial_common.py",
            target / "trial_common.py",
            0o644,
        ),
        (
            "/usr/lib/samurai-charging/trial_guard.py",
            target / "trial_guard.py",
            0o755,
        ),
    ):
        row = manifest["device_files"][target_path]
        row["sha256"] = sha256_file(source)
        row["mode"] = mode
    return manifest


def rewrite_fastboot_operator(
    path: Path,
    *,
    manifest_sha256: str,
    image_sha256: str,
    image_bytes: int,
    kernel_build_label: str,
) -> None:
    text = path.read_text(encoding="utf-8")
    text, count = re.subn(
        r"(\$script:ExpectedProductionManifestSha256 = ')[0-9a-f]{64}(')",
        rf"\g<1>{manifest_sha256}\g<2>",
        text,
    )
    if count != 1:
        raise PreparationError("fastboot operator production manifest pin not found")
    text = _replace_required(
        text,
        CURRENT_IMAGE_SHA256,
        image_sha256,
        "fastboot operator current Image hash",
    )
    text = _replace_required(
        text,
        str(CURRENT_IMAGE_BYTES),
        str(image_bytes),
        "fastboot operator current Image size",
    )
    text = _replace_required(
        text,
        "production #517 Image",
        f"production {kernel_build_label} Image",
        "fastboot operator Image label",
    )
    path.write_text(text, encoding="utf-8", newline="\n")


def generated_readme(plan: dict) -> str:
    image = plan["image"]
    boot = plan["carriers"]["boot"]["new"]
    logdump = plan["carriers"]["logdump"]["new"]
    primary = plan["modules"][PRIMARY_MODULE_NAME]["new"]
    usb = plan["modules"][USB_MODULE_NAME]["new"]
    return f"""# Trial {plan["trial_id"]}

This is the r8 status/Full and precharge full-boot trial. It was materialized
offline by `prepare-trial-517-r8.py`; no phone, SSH, adb, fastboot, device
wrapper, reboot, or charging-hardware operation was performed.

## Pins

- Kernel version: `{plan["kernel_version"]}`
- Kernel release: `{plan["kernel_release"]}`
- Image: `{image["sha256"]}` ({image["bytes"]} bytes)
- New boot: `{boot["sha256"]}`
- New logdump/FAT: `{logdump["sha256"]}`
- `samurai-mp2650.ko`: `{primary["sha256"]}`
- `samurai-usb-input.ko`: `{usb["sha256"]}`
- Rollback boot: `{CURRENT_BOOT_SHA256}`
- Rollback Image: `{CURRENT_IMAGE_SHA256}`

The manifest requires the built-in `vmlinux` export
`{BQ_SYMBOL}` with owner `vmlinux` and type `EXPORT_SYMBOL_GPL`.

## Scope

The package replaces the current boot and logdump while preserving the current
#517 boot/Image as the rollback baseline. It installs both the primary MP2650
module and the existing wake USB module, updates all trial userspace files, and
patches only the matching entries in the main charging manifest.

High voltage, PD/PPS/QC takeover, charger-register experiments, and device
hot-unload are outside this package.

## Required gates

1. Run the local test suite from this directory.
2. Review `TRIAL-R8-PREPARATION.json` and confirm every SHA-256 is final.
3. Run stage preflight and require the exact kernel version and main-manifest
   old hash recorded in `manifest.json`.
4. Execute stage only after the guard tests and preflight pass.
5. Continue with the fastboot operator; it writes logdump then boot and allows
   one reboot.
6. After boot, require accepted state, both module hashes, the new main
   manifest hash, protection Good, NCM, Type-C, and MP2650 telemetry.

Physical low-battery precharge and Full/recharge behavior are not proven by
this package and must be validated on the new boot.
"""


def generated_commands(plan: dict) -> str:
    target = Path(plan["target_trial"])
    return f"""# Commands for {plan["trial_id"]}

No command below was executed while this scaffold was prepared.

## Local verification

```powershell
cd "{target}"
python tests\\run_tests.py
```

## Inspection before deployment

```powershell
python -B "{Path(__file__).resolve()}" --self-check
Get-Content -Raw .\\manifest.json
Get-Content -Raw .\\TRIAL-R8-PREPARATION.json
```

## Operator sequence

Use an SDP/5 V source only. Stop if the main-manifest hash on the device is not
the exact `main_manifest.old_sha256` in `manifest.json`.

1. Upload this directory to a new, unique remote package path.
2. Run `python3 -B trial_stage.py --package . --serial 62bc28a1` as preflight.
3. Require `stage_mode=carrier`, `restart_mode=bootloader`, and no carrier write.
4. Run stage with `--execute`; it installs userspace and both modules, then
   enters the bootloader once.
5. Run `fastboot_operator.ps1` with the stage receipt. It writes logdump first,
   boot second, and reboots once.
6. If the guard rejects the new boot, keep the generated rollback evidence and
   do not manually issue another reboot.

## New-boot acceptance

```powershell
$Key = "E:\\edk2-samurai-out\\kernel72\\id_ed25519"
$Known = "E:\\edk2-samurai-out\\kernel109\\known_hosts-pmos"
ssh -i $Key -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes `
  -o UserKnownHostsFile=$Known root@169.254.42.1 `
  "cat {plan["device_root"]}/state.json; sha256sum /usr/share/samurai-charging/manifest.json; sha256sum /lib/modules/{plan["kernel_release"]}/extra/samurai-charging/samurai-mp2650.ko; sha256sum /lib/modules/{plan["kernel_release"]}/extra/samurai-charging/samurai-usb-input.ko"
```

The guard must reach `accepted` on the new boot before any new soak is counted.
"""


def write_sha256sums(root: Path) -> None:
    rows = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == "SHA256SUMS":
            continue
        if path.name.startswith(("test-results", "test-run-")):
            continue
        if "__pycache__" in path.relative_to(root).parts:
            continue
        rows.append(f"{sha256_file(path)}  {path.relative_to(root).as_posix()}")
    (root / "SHA256SUMS").write_text(
        "\n".join(rows) + "\n", encoding="utf-8", newline="\n"
    )


def materialize(args: argparse.Namespace) -> dict:
    plan = build_plan(args)
    target = Path(args.target_trial).resolve()
    expected_parent = ROOT.resolve()
    if target.parent != expected_parent:
        raise PreparationError("target trial must be a direct child of the integration root")
    if not target.name.startswith("trial-517-r8-"):
        raise PreparationError("target trial name must start with trial-517-r8-")
    if target.exists() or target.is_symlink():
        raise PreparationError(f"refusing to overwrite existing target: {target}")

    preparing = target.with_name("." + target.name + ".preparing")
    if preparing.exists() or preparing.is_symlink():
        raise PreparationError(f"stale preparation directory exists: {preparing}")

    def ignore(directory: str, names: list[str]) -> set[str]:
        ignored = set()
        for name in names:
            if name in SKIP_NAMES or name == "modules":
                ignored.add(name)
        return ignored

    try:
        shutil.copytree(
            SOURCE_TRIAL,
            preparing,
            ignore=ignore,
            copy_function=shutil.copy2,
        )
        modules = preparing / "modules"
        modules.mkdir(mode=0o755)
        shutil.copy2(args.mp2650_module, modules / "samurai-mp2650.ko")
        shutil.copy2(args.usb_module, modules / "samurai-usb-input.ko")

        rewrite_trial_common(
            preparing / "trial_common.py",
            trial_id=plan["trial_id"],
            token=plan["token"],
            kernel_version=plan["kernel_version"],
            release=plan["kernel_release"],
            device_root=plan["device_root"],
            main_manifest_sha256=plan["main_manifest_old_sha256"],
            image_sha256=plan["image"]["sha256"],
            image_bytes=plan["image"]["bytes"],
            boot_new_sha256=plan["carriers"]["boot"]["new"]["sha256"],
            logdump_new_sha256=plan["carriers"]["logdump"]["new"]["sha256"],
            primary_new_sha256=plan["modules"][PRIMARY_MODULE_NAME]["new"]["sha256"],
            primary_new_bytes=plan["modules"][PRIMARY_MODULE_NAME]["new"]["bytes"],
            usb_old_sha256=plan["modules"][USB_MODULE_NAME]["old"]["sha256"],
            usb_old_bytes=plan["modules"][USB_MODULE_NAME]["old"]["bytes"],
            usb_new_sha256=plan["modules"][USB_MODULE_NAME]["new"]["sha256"],
            usb_new_bytes=plan["modules"][USB_MODULE_NAME]["new"]["bytes"],
        )
        rewrite_text_crossrefs(
            preparing,
            trial_id=plan["trial_id"],
            token=plan["token"],
            kernel_version=plan["kernel_version"],
            release=plan["kernel_release"],
            device_root=plan["device_root"],
            target_name=target.name,
        )
        service_path = preparing / "service/samurai-charging"
        service_text = service_path.read_text(encoding="utf-8")
        service_text = _replace_required(
            service_text,
            "with the #517 rollback guard",
            f"with the {plan['kernel_build_label']} rollback guard",
            "service kernel label",
        )
        service_path.write_text(
            service_text, encoding="utf-8", newline="\n"
        )
        manifest = build_manifest(
            source_manifest_path=SOURCE_TRIAL / "manifest.json",
            target=preparing,
            plan=plan,
            kernel_version=plan["kernel_version"],
            release=plan["kernel_release"],
            trial_id=plan["trial_id"],
            token=plan["token"],
            device_root=plan["device_root"],
            image_path=plan["image"]["path"],
            image_sha256=plan["image"]["sha256"],
            image_bytes=plan["image"]["bytes"],
            boot_new_path=Path(args.boot),
            boot_new_sha256=plan["carriers"]["boot"]["new"]["sha256"],
            logdump_new_path=Path(args.logdump),
            logdump_new_sha256=plan["carriers"]["logdump"]["new"]["sha256"],
            dtb_path=Path(args.dtb),
            dtb_sha256=args.dtb_sha256,
            dtb_bytes=args.dtb_bytes,
            fat_receipt_path=Path(args.fat_receipt),
            boot_receipt_path=Path(args.boot_receipt),
            primary_module_sha256=plan["modules"][PRIMARY_MODULE_NAME]["new"]["sha256"],
            primary_module_bytes=plan["modules"][PRIMARY_MODULE_NAME]["new"]["bytes"],
            usb_old_sha256=plan["modules"][USB_MODULE_NAME]["old"]["sha256"],
            usb_old_bytes=plan["modules"][USB_MODULE_NAME]["old"]["bytes"],
            usb_module_sha256=plan["modules"][USB_MODULE_NAME]["new"]["sha256"],
            usb_module_bytes=plan["modules"][USB_MODULE_NAME]["new"]["bytes"],
            main_manifest_sha256=plan["main_manifest_old_sha256"],
        )
        manifest_path = preparing / "manifest.json"
        manifest_path.write_bytes(canonical_json_bytes(manifest))
        manifest_sha256 = sha256_file(manifest_path)

        rewrite_fastboot_operator(
            preparing / "fastboot_operator.ps1",
            manifest_sha256=manifest_sha256,
            image_sha256=plan["image"]["sha256"],
            image_bytes=plan["image"]["bytes"],
            kernel_build_label=plan["kernel_build_label"],
        )
        (preparing / "README.md").write_text(
            generated_readme(plan), encoding="utf-8", newline="\n"
        )
        (preparing / "COMMANDS.md").write_text(
            generated_commands(plan), encoding="utf-8", newline="\n"
        )

        final_plan = {
            **plan,
            "materialized": True,
            "manifest_sha256": manifest_sha256,
            "fastboot_operator_sha256": sha256_file(
                preparing / "fastboot_operator.ps1"
            ),
            "readme_sha256": sha256_file(preparing / "README.md"),
            "commands_sha256": sha256_file(preparing / "COMMANDS.md"),
        }
        (preparing / "TRIAL-R8-PREPARATION.json").write_bytes(
            canonical_json_bytes(final_plan)
        )
        package_result = {
            "schema": 1,
            "trial_id": plan["trial_id"],
            "status": "prepared-not-built",
            "package_built": False,
            "runtime_acceptance_pending": True,
            "tests": {"status": "pending", "passed": False},
            "manifest_sha256": manifest_sha256,
            "source_manifest_sha256": SOURCE_MANIFEST_SHA256,
            "image": plan["image"],
            "modules": plan["modules"],
            "bq27xxx_evidence": plan["bq27xxx_evidence"],
            "phone_or_fastboot_accessed": False,
            "device_rebooted": False,
        }
        (preparing / "package-result.json").write_bytes(
            canonical_json_bytes(package_result)
        )
        write_sha256sums(preparing)

        if target.exists() or target.is_symlink():
            raise PreparationError(
                f"target appeared while preparing; refusing overwrite: {target}"
            )
        os.replace(preparing, target)
    except BaseException:
        if preparing.exists() and not target.exists():
            shutil.rmtree(preparing)
        raise

    return {
        **plan,
        "materialized": True,
        "target_trial": str(target),
        "manifest_sha256": sha256_file(target / "manifest.json"),
        "preparation_receipt": str(target / "TRIAL-R8-PREPARATION.json"),
    }


def self_check() -> dict:
    checks = {}
    for relative in SOURCE_FILES_REQUIRED:
        path = require_regular(SOURCE_TRIAL / relative, f"source trial {relative}")
        checks[relative] = {"sha256": sha256_file(path), "bytes": path.stat().st_size}
    manifest = SOURCE_TRIAL / "manifest.json"
    actual_manifest = sha256_file(manifest)
    if actual_manifest != SOURCE_MANIFEST_SHA256:
        raise PreparationError(
            "source trial-517-wake-r1/manifest.json changed unexpectedly: "
            f"{actual_manifest}"
        )
    usb = pin_file(
        USB_MODULE_DEFAULT,
        USB_MODULE_NEW_SHA256,
        expected_bytes=USB_MODULE_NEW_BYTES,
        label="source wake USB module",
    )
    current_boot = pin_file(
        CURRENT_BOOT,
        CURRENT_BOOT_SHA256,
        expected_bytes=100_663_296,
        label="current rollback boot",
    )
    current_logdump = pin_file(
        CURRENT_LOGDUMP,
        CURRENT_LOGDUMP_SHA256,
        expected_bytes=LOGDUMP_BYTES,
        label="current rollback logdump",
    )
    current_image = pin_file(
        CURRENT_IMAGE_HOST_PATH,
        CURRENT_IMAGE_SHA256,
        expected_bytes=CURRENT_IMAGE_BYTES,
        label="current rollback Image",
    )
    dtb = pin_file(
        DTB,
        DTB_SHA256,
        expected_bytes=DTB_BYTES,
        label="runtime DTB",
    )
    if TARGET_TRIAL.exists() or TARGET_TRIAL.is_symlink():
        raise PreparationError(
            f"final target already exists; scaffold will not overwrite it: {TARGET_TRIAL}"
        )
    return {
        "schema": "samurai-trial-r8-self-check-v1",
        "passed": True,
        "mode": "read-only",
        "source_trial": str(SOURCE_TRIAL),
        "target_trial": str(TARGET_TRIAL),
        "target_absent": True,
        "source_manifest_sha256": actual_manifest,
        "source_usb_module": usb,
        "current_rollback": {
            "boot": current_boot,
            "logdump": current_logdump,
            "image": current_image,
            "dtb": dtb,
        },
        "required_unresolved_inputs": [
            "new Image manifest path and host-readable file",
            "new Image SHA-256 and byte size",
            "new kernel release and exact #N build label",
            "new boot path, size, hash, and boot receipt",
            "new logdump/FAT path, hash, and FAT receipt",
            "new samurai-mp2650.ko path, hash, and size",
            "Module.symvers containing the built-in GPL bq27xxx export",
            "current main-manifest hash after the chosen wake-r1 install order",
        ],
        "device_or_fastboot_accessed": False,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare the r8 full-boot trial offline. Default is plan-only; "
            "--materialize creates a new target and refuses overwrite."
        )
    )
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--materialize", action="store_true")
    parser.add_argument("--source-trial", type=Path, default=SOURCE_TRIAL)
    parser.add_argument("--target-trial", type=Path, default=TARGET_TRIAL)
    parser.add_argument("--trial-id", default=PLANNED_TRIAL_ID)
    parser.add_argument("--device-root", default=PLANNED_DEVICE_ROOT)
    parser.add_argument("--token")
    parser.add_argument("--image", help="Image path recorded in the final manifest")
    parser.add_argument("--image-file", type=Path, help="host-readable new Image")
    parser.add_argument("--image-sha256")
    parser.add_argument("--image-bytes", type=int)
    parser.add_argument("--kernel-version")
    parser.add_argument("--kernel-build-label")
    parser.add_argument("--kernel-release")
    parser.add_argument("--build-root", type=Path)
    parser.add_argument("--boot", type=Path)
    parser.add_argument("--boot-sha256")
    parser.add_argument("--boot-bytes", type=int, default=100_663_296)
    parser.add_argument("--boot-receipt", type=Path)
    parser.add_argument(
        "--allow-identical-boot",
        action="store_true",
        help=(
            "allow the proven rollback boot when the kernel is delivered only "
            "through the new FAT Image"
        ),
    )
    parser.add_argument("--fat-receipt", type=Path)
    parser.add_argument("--logdump", type=Path)
    parser.add_argument("--logdump-sha256")
    parser.add_argument("--mp2650-module", type=Path)
    parser.add_argument("--mp2650-module-sha256")
    parser.add_argument("--usb-module", type=Path, default=USB_MODULE_DEFAULT)
    parser.add_argument("--usb-module-sha256", default=USB_MODULE_NEW_SHA256)
    parser.add_argument("--usb-old-sha256", default=USB_MODULE_OLD_SHA256)
    parser.add_argument("--usb-old-bytes", type=int, default=USB_MODULE_OLD_BYTES)
    parser.add_argument("--main-manifest-sha256")
    parser.add_argument("--dtb", type=Path, default=DTB)
    parser.add_argument("--dtb-sha256", default=DTB_SHA256)
    parser.add_argument("--dtb-bytes", type=int, default=DTB_BYTES)
    args = parser.parse_args(argv)

    if args.source_trial.resolve() != SOURCE_TRIAL.resolve():
        raise PreparationError(
            "this scaffold is intentionally pinned to trial-517-wake-r1 as source"
        )
    if args.kernel_version and args.kernel_build_label is None:
        args.kernel_build_label = args.kernel_version.split(maxsplit=1)[0]
    return args


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        if args.self_check:
            print(json.dumps(self_check(), indent=2, sort_keys=True))
            return 0
        if args.materialize:
            result = materialize(args)
        else:
            result = build_plan(args)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except PreparationError as error:
        print(f"prepare-trial-517-r8: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
