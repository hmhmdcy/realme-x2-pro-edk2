#!/usr/bin/env python3
"""Validate the offline UEFI/GRUB standard-boot candidate."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import struct
import sys
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require_file(path: Path, failures: list[str]) -> bool:
    if path.is_file():
        return True
    failures.append(f"missing file: {path}")
    return False


def pe_machine(path: Path) -> int:
    data = path.read_bytes()
    if data[:2] != b"MZ":
        raise ValueError(f"not a PE image: {path}")
    pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe_offset:pe_offset + 4] != b"PE\0\0":
        raise ValueError(f"missing PE signature: {path}")
    return struct.unpack_from("<H", data, pe_offset + 4)[0]


def contains_utf16(data: bytes, value: str) -> bool:
    return value.encode("utf-16le") in data


def contains_ascii(data: bytes, value: str) -> bool:
    return value.encode("ascii") in data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--candidate-dir",
        type=Path,
        default=Path(
            "E:/edk2-samurai-out/standard-arm64-v731/"
            "uefi-standard-boot-candidate"
        ),
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.candidate_dir.resolve()
    failures: list[str] = []
    checks: dict[str, object] = {}

    manifest_path = root / "MANIFEST.json"
    verification_path = root / "verification.json"
    if not require_file(manifest_path, failures):
        return report(root, failures, checks, args.output)
    if not require_file(verification_path, failures):
        return report(root, failures, checks, args.output)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    verification = json.loads(verification_path.read_text(encoding="utf-8"))
    checks["manifest_status"] = manifest.get("status")
    checks["verification_status"] = verification.get("status")
    if manifest.get("status") != "offline_built_not_flashed":
        failures.append("candidate manifest is not offline_built_not_flashed")
    if verification.get("status") != "offline_verified_not_flashed":
        failures.append("verification status is not offline_verified_not_flashed")

    artifact_paths = {
        "platform_bm_source": "PlatformBm.c",
        "bds": "bds/BdsDxe.efi",
        "boot": "boot-image/boot-eud-production-off.img",
        "grub": "BOOTAA64.EFI",
        "kernel_fat": "kernel-fat-standard-uefi.img",
        "image": "Image-v731-standard",
        "dtb": "sm8150-samurai-v731.dtb",
    }
    for name, relative in artifact_paths.items():
        path = root / relative
        if not require_file(path, failures):
            continue
        expected = manifest["artifacts"][name]["sha256"]
        actual = sha256(path)
        checks[f"{name}_sha256"] = actual
        if actual != expected:
            failures.append(f"{name} hash mismatch: {actual} != {expected}")

    bds = root / "bds/BdsDxe.efi"
    grub = root / "BOOTAA64.EFI"
    grub_config = root / "grub.cfg"
    if bds.is_file():
        if pe_machine(bds) != 0xAA64:
            failures.append("BdsDxe is not an ARM64 PE image")
        text = bds.read_bytes()
        checks["bds_standard_path"] = contains_utf16(
            text, r"\EFI\BOOT\BOOTAA64.EFI"
        )
        checks["bds_direct_fallback"] = contains_utf16(text, r"\Image")
        if not checks["bds_standard_path"]:
            failures.append("BdsDxe lacks the standard removable-media path")
        if not checks["bds_direct_fallback"]:
            failures.append("BdsDxe lacks the direct /Image fallback")

    if grub.is_file():
        if pe_machine(grub) != 0xAA64:
            failures.append("BOOTAA64.EFI is not an ARM64 PE image")
        text = grub.read_bytes()
        for needle in (
            "search --no-floppy --file --set=root /Image",
            "linux /Image",
            "devicetree /samurai.dtb",
            "root=PARTLABEL=userdata",
        ):
            present = contains_ascii(text, needle)
            checks[f"grub_{needle}"] = present
            if not present:
                failures.append(f"GRUB image lacks: {needle}")
        checks["grub_no_volume_label_dependency"] = not contains_ascii(
            text, "--label KERNEL"
        )
        if not checks["grub_no_volume_label_dependency"]:
            failures.append("GRUB image still searches for the KERNEL volume label")
        checks["grub_search_fs_file"] = contains_ascii(text, "search_fs_file")
        if not checks["grub_search_fs_file"]:
            failures.append("GRUB image does not embed search_fs_file")

    if require_file(grub_config, failures):
        config_text = grub_config.read_text(encoding="utf-8")
        config_hash = sha256(grub_config)
        expected_config_hash = manifest["artifacts"]["grub"].get(
            "config_sha256"
        )
        checks["grub_config_sha256"] = config_hash
        if config_hash != expected_config_hash:
            failures.append(
                "grub.cfg hash mismatch: "
                f"{config_hash} != {expected_config_hash}"
            )
        checks["grub_config_file_search"] = (
            "search --no-floppy --file --set=root /Image" in config_text
        )
        checks["grub_config_no_label"] = "--label KERNEL" not in config_text
        if not checks["grub_config_file_search"]:
            failures.append("grub.cfg does not discover the volume by /Image")
        if not checks["grub_config_no_label"]:
            failures.append("grub.cfg still depends on the KERNEL volume label")

    boot = root / "boot-image/boot-eud-production-off.img"
    if bds.is_file() and boot.is_file():
        builder_path = Path(__file__).with_name("build-boot-larger.py")
        spec = importlib.util.spec_from_file_location("boot_builder", builder_path)
        if spec is None or spec.loader is None:
            failures.append("cannot load build-boot-larger.py")
        else:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            parsed = module.parse_boot(boot.read_bytes())
            bds_ffs = next(
                item for item in parsed["main_files"]
                if item["guid"] == module.BDS_GUID
            )
            sections = module.ffs_sections(bds_ffs["full"])
            pe32 = next(item["body"] for item in sections if item["type"] == 0x10)
            checks["bds_pe32_in_boot"] = hashlib.sha256(pe32).hexdigest()
            if checks["bds_pe32_in_boot"] != sha256(bds):
                failures.append("boot image BDS PE32 does not match BdsDxe.efi")

    review_path = root / "metadata-review.json"
    if require_file(review_path, failures):
        review = json.loads(review_path.read_text(encoding="utf-8"))
        checks["metadata_review_classification"] = review.get("classification")
        modules = review.get("metadata_modules", {})
        for name in ("PlatformSmbiosDxe", "UiApp"):
            if modules.get(name, {}).get("classification") != "identical":
                failures.append(f"{name} is not byte-identical in metadata review")
        if review.get("classification") != "requires_manual_review":
            failures.append("BDS code change is not classified for manual review")

    helper = Path(__file__).with_name("flash-v731-uefi-standard.ps1")
    if require_file(helper, failures):
        text = helper.read_text(encoding="utf-8")
        checks["flash_helper_sha256"] = sha256(helper)
        expected_helper_hash = manifest["flash_contract"].get("helper_sha256")
        if checks["flash_helper_sha256"] != expected_helper_hash:
            failures.append(
                "flash helper hash mismatch: "
                f"{checks['flash_helper_sha256']} != {expected_helper_hash}"
            )
        checks["flash_helper_pair_guard"] = (
            "-FlashBoot" in text and "-FlashKernelFat" in text
            and "partial flashing is rejected" in text
        )
        if not checks["flash_helper_pair_guard"]:
            failures.append("flash helper does not enforce the paired write")

    checks["not_flashed"] = verification.get("not_tested", {}).get("flashed") is False
    if not checks["not_flashed"]:
        failures.append("verification does not record the unflashed state")

    return report(root, failures, checks, args.output)


def report(
    root: Path,
    failures: list[str],
    checks: dict[str, object],
    output: Path | None,
) -> int:
    result = {
        "schema": "samurai-uefi-standard-candidate-check-v1",
        "candidate_dir": str(root),
        "passed": not failures,
        "checks": checks,
        "failures": failures,
    }
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if output:
        output.write_text(rendered, encoding="utf-8")
    sys.stdout.write(rendered)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
