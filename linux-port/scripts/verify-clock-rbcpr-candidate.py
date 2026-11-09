#!/usr/bin/env python3
"""Validate the offline clock RBCPR candidate and its build proof."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
DEFAULT_ROOT = Path(
    "E:/edk2-samurai-out/standard-arm64-v731/clock-rbcpr-candidate"
)

EXPECTED = {
    "image": (
        "Image-v731-clock-rbcpr",
        44300800,
        "9d50f46424a64c9ce7ff5277ea2abab18480df1b23a78c7d2199a9bc261d925e",
    ),
    "grub": (
        "BOOTAA64.EFI",
        1007616,
        "81fba9922e74259001495ae1ae7368744f940d6b9e2d4c3feeaf173fd0459887",
    ),
    "config": (
        "grub.cfg",
        697,
        "2cce9fa843c64956a72f124c22e77284e550395ef496195e4c5cce8bc99a9b6b",
    ),
    "kernel_fat": (
        "kernel-fat-clock-rbcpr.img",
        67108864,
        "3e788ccbf9fa598f43c25be7747a0571742e21df18b4bb8f5917def2ed65117a",
    ),
    "boot": (
        "boot-eud-clock-rbcpr.img",
        100663296,
        "c5e856d5ac06a42fb55df909dae26fe26293517aa65fd67570730f6de068690c",
    ),
    "patch": (
        "object-proof/0003-clk-qcom-gcc-sm8150-keep-cpuss-rbcpr-critical.patch",
        951,
        "3955ff1e889a0ae8c42e8356615bcbc6bcbafe900a615fb958080bf4982ff203",
    ),
    "baseline_object": (
        "object-proof/gcc-sm8150-baseline.o",
        148928,
        "c81064b8615976ebbe713c8287c8bb512310de0d5efe32aa3ee8090e6e4de8d1",
    ),
    "patched_object": (
        "object-proof/gcc-sm8150-patched.o",
        148928,
        "38c36a14102706fe524049803d5f59b0e9d9ec2ff6d1658ef2b803fe86745e71",
    ),
}

PATCH_REPO_PATH = (
    REPO
    / "linux-port/patches/v7.3.1/"
    "0003-clk-qcom-gcc-sm8150-keep-cpuss-rbcpr-critical.patch"
)
SOURCE_CONFIG = REPO / "linux-port/uefi-standard/grub-clock-rbcpr.cfg"
FLASH_HELPER = REPO / "linux-port/scripts/flash-v731-clock-rbcpr.ps1"
CONFIG_SHA256 = "d3dc6f072055a7d9da50de7c1e5416da837c680c00126f9a8f25b379f9984097"
CONFIG_SOURCE_SHA256 = "2cce9fa843c64956a72f124c22e77284e550395ef496195e4c5cce8bc99a9b6b"
HELPER_SHA256 = "878caaaf0889b82326364bc6c18d708be0d3577b18c1c8b591edd044b970dd3f"
BDS_PE_SHA256 = "f5cf8a7efcce6208ef48250928880214ae25807ea92c17e0d896547f87f57206"
DTB_SHA256 = "3799ec6c7d3e0c67a657859a37b2fe147fa21a9dedc84d49c8eb83fd8debc805"
CLK_IS_CRITICAL_BIT = 11
FLAGS_OFFSET = 0x7118


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run(
    argv: list[str],
    timeout: int = 60,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            argv,
            check=False,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            env=env,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as error:
        return subprocess.CompletedProcess(argv, 127, str(error))


def require(path: Path, failures: list[str]) -> bool:
    if path.is_file():
        return True
    failures.append(f"missing file: {path}")
    return False


def read_json(path: Path, failures: list[str]) -> dict:
    if not require(path, failures):
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        failures.append(f"invalid JSON {path}: {error}")
        return {}


def pe_machine(path: Path) -> int:
    data = path.read_bytes()
    if data[:2] != b"MZ":
        raise ValueError(f"not a PE image: {path}")
    offset = struct.unpack_from("<I", data, 0x3C)[0]
    if data[offset:offset + 4] != b"PE\0\0":
        raise ValueError(f"missing PE signature: {path}")
    return struct.unpack_from("<H", data, offset + 4)[0]


def contains_ascii(data: bytes, value: str) -> bool:
    return value.encode("ascii") in data


def find_seven_zip(explicit: str | None) -> Path | None:
    candidates = []
    if explicit:
        candidates.append(explicit)
    for name in ("7z", "7za"):
        found = shutil.which(name)
        if found:
            candidates.append(found)
    candidates.extend(
        [
            r"C:\Program Files\7-Zip\7z.exe",
            r"C:\Program Files (x86)\7-Zip\7z.exe",
            "/usr/bin/7z",
            "/usr/bin/7za",
        ]
    )
    for candidate in candidates:
        path = Path(candidate)
        if path.is_file():
            return path
    return None


def fat_entries(seven_zip: Path, image: Path, failures: list[str]) -> dict[str, dict[str, str]]:
    result = run([str(seven_zip), "l", "-slt", "-ba", str(image)], timeout=120)
    if result.returncode != 0:
        failures.append(f"7z could not list FAT image: {result.stdout.strip()}")
        return {}
    entries: dict[str, dict[str, str]] = {}
    current: dict[str, str] = {}
    for line in result.stdout.splitlines() + [""]:
        if not line.strip():
            path = current.get("Path")
            if path:
                entries[path.replace("\\", "/")] = current
            current = {}
            continue
        if " = " in line:
            key, value = line.split(" = ", 1)
            current[key] = value
    return entries


def fat_member_sha256(seven_zip: Path, image: Path, member: str, failures: list[str]) -> str:
    process = subprocess.Popen(
        [str(seven_zip), "x", "-so", str(image), member],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    digest = hashlib.sha256()
    try:
        assert process.stdout is not None
        for block in iter(lambda: process.stdout.read(4 * 1024 * 1024), b""):
            digest.update(block)
        stderr = process.stderr.read().decode("utf-8", "replace") if process.stderr else ""
        returncode = process.wait()
    finally:
        if process.poll() is None:
            process.kill()
    if returncode != 0:
        failures.append(f"7z could not read {member}: {stderr.strip()}")
        return ""
    return digest.hexdigest()


def windows_to_wsl_path(path: Path) -> str:
    resolved = path.resolve()
    drive = resolved.drive
    if len(drive) == 2 and drive[1] == ":":
        relative = resolved.as_posix()[3:]
        return f"/mnt/{drive[0].lower()}/{relative}"
    return resolved.as_posix()


def fsck_fat(image: Path, failures: list[str]) -> tuple[bool, str]:
    if os.name == "nt":
        wsl = shutil.which("wsl.exe") or r"C:\Windows\System32\wsl.exe"
        if not Path(wsl).is_file():
            failures.append("wsl.exe is unavailable for fsck.vfat")
            return False, ""
        wsl_env = os.environ.copy()
        wsl_env["WSL_UTF8"] = "1"
        result = run(
            [wsl, "-e", "/usr/sbin/fsck.vfat", "-n", windows_to_wsl_path(image)],
            timeout=120,
            env=wsl_env,
        )
    else:
        fsck = "/usr/sbin/fsck.vfat" if Path("/usr/sbin/fsck.vfat").is_file() else "fsck.vfat"
        result = run([fsck, "-n", str(image)], timeout=120)
    output = "\n".join(
        line
        for line in (result.stdout or "").splitlines()
        if not line.startswith("wsl:")
    ).strip()
    if result.returncode != 0:
        failures.append(f"fsck.vfat failed: {output}")
        return False, output
    return True, output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-dir", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--seven-zip")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.candidate_dir.resolve()
    failures: list[str] = []
    checks: dict[str, object] = {}

    manifest = read_json(root / "MANIFEST.json", failures)
    verification = read_json(root / "verification.json", failures)
    build_receipt = read_json(root / "object-proof/build-receipt.json", failures)
    verification_path = root / "verification.json"
    build_receipt_path = root / "object-proof/build-receipt.json"
    checks["manifest_status"] = manifest.get("status")
    checks["verification_status"] = verification.get("status")
    checks["build_receipt_status"] = build_receipt.get("status")
    if manifest.get("schema") != "samurai-clock-rbcpr-candidate-v1":
        failures.append("unexpected candidate manifest schema")
    if manifest.get("status") != "offline_built_not_flashed":
        failures.append("candidate manifest is not offline_built_not_flashed")
    if verification.get("status") != "offline_verified_not_flashed":
        failures.append("verification status is not offline_verified_not_flashed")
    if build_receipt.get("status") != "verified_object_rebuild":
        failures.append("build receipt status is not verified_object_rebuild")
    if verification_path.is_file():
        verification_hash = sha256(verification_path)
        checks["verification_sha256"] = verification_hash
        if manifest.get("verification", {}).get("sha256") != verification_hash:
            failures.append("manifest verification hash does not match verification.json")
    if build_receipt_path.is_file():
        receipt_hash = sha256(build_receipt_path)
        checks["build_receipt_sha256"] = receipt_hash
        if manifest.get("artifacts", {}).get("build_receipt", {}).get("sha256") != receipt_hash:
            failures.append("manifest build receipt hash does not match")

    for name, (relative, expected_bytes, expected_hash) in EXPECTED.items():
        path = root / relative
        if not require(path, failures):
            continue
        actual_bytes = path.stat().st_size
        actual_hash = sha256(path)
        checks[f"{name}_bytes"] = actual_bytes
        checks[f"{name}_sha256"] = actual_hash
        if actual_bytes != expected_bytes:
            failures.append(f"{name} size mismatch: {actual_bytes} != {expected_bytes}")
        if actual_hash != expected_hash:
            failures.append(f"{name} hash mismatch: {actual_hash} != {expected_hash}")
        manifest_entry = manifest.get("artifacts", {}).get(name, {})
        if manifest_entry.get("sha256") != expected_hash:
            failures.append(f"manifest {name} hash does not match the locked value")

    if PATCH_REPO_PATH.is_file():
        checks["repo_patch_sha256"] = sha256(PATCH_REPO_PATH)
        if checks["repo_patch_sha256"] != EXPECTED["patch"][2]:
            failures.append("repository clock patch hash changed")
    else:
        failures.append("repository clock patch is missing")

    if SOURCE_CONFIG.is_file():
        checks["source_grub_config_sha256"] = sha256(SOURCE_CONFIG)
        if checks["source_grub_config_sha256"] != CONFIG_SOURCE_SHA256:
            failures.append("source grub-clock-rbcpr.cfg changed")
    else:
        failures.append("source grub-clock-rbcpr.cfg is missing")

    config_path = root / "grub.cfg"
    if config_path.is_file():
        config_text = config_path.read_text(encoding="utf-8")
        checks["grub_config_file_search"] = (
            "search --no-floppy --file --set=root /Image" in config_text
        )
        checks["grub_config_no_safety_flag"] = "clk_ignore_unused" not in config_text
        checks["grub_config_no_label_dependency"] = "--label KERNEL" not in config_text
        if not checks["grub_config_file_search"]:
            failures.append("grub.cfg does not search for the FAT by /Image")
        if not checks["grub_config_no_safety_flag"]:
            failures.append("grub.cfg still contains clk_ignore_unused")
        if not checks["grub_config_no_label_dependency"]:
            failures.append("grub.cfg still depends on the KERNEL volume label")

    grub_path = root / "BOOTAA64.EFI"
    if grub_path.is_file():
        try:
            checks["grub_pe_machine"] = hex(pe_machine(grub_path))
            if checks["grub_pe_machine"] != "0xaa64":
                failures.append("BOOTAA64.EFI is not an ARM64 PE image")
        except ValueError as error:
            failures.append(str(error))
        text = grub_path.read_bytes()
        required_strings = (
            "search --no-floppy --file --set=root /Image",
            "samurai: clock RBCPR candidate, safety flag removed",
            "linux /Image console=tty0 loglevel=4 panic=15 root=PARTLABEL=userdata "
            "rootfstype=f2fs rootwait rw",
            "devicetree /samurai.dtb",
            "search_fs_file",
        )
        for needle in required_strings:
            present = contains_ascii(text, needle)
            checks[f"grub_string_{needle}"] = present
            if not present:
                failures.append(f"GRUB image lacks: {needle}")
        checks["grub_efi_no_safety_flag"] = not contains_ascii(text, "clk_ignore_unused")
        checks["grub_efi_no_label_dependency"] = not contains_ascii(text, "--label KERNEL")
        if not checks["grub_efi_no_safety_flag"]:
            failures.append("GRUB EFI still contains clk_ignore_unused")
        if not checks["grub_efi_no_label_dependency"]:
            failures.append("GRUB EFI still depends on the KERNEL label")

    seven_zip = find_seven_zip(args.seven_zip)
    if seven_zip is None:
        failures.append("7z is required to verify FAT contents")
    else:
        checks["seven_zip"] = str(seven_zip)
        fat = root / EXPECTED["kernel_fat"][0]
        if fat.is_file():
            entries = fat_entries(seven_zip, fat, failures)
            for member, expected_hash in (
                ("Image", EXPECTED["image"][2]),
                ("samurai.dtb", DTB_SHA256),
                ("EFI/BOOT/BOOTAA64.EFI", EXPECTED["grub"][2]),
            ):
                checks[f"fat_member_{member}"] = member in entries
                if member not in entries:
                    failures.append(f"FAT member missing: {member}")
                    continue
                actual_hash = fat_member_sha256(seven_zip, fat, member, failures)
                checks[f"fat_{member}_sha256"] = actual_hash
                if actual_hash != expected_hash:
                    failures.append(f"FAT {member} hash mismatch: {actual_hash}")
        fsck_ok, fsck_output = fsck_fat(fat, failures)
        checks["fat_fsck_clean"] = fsck_ok
        checks["fat_fsck_output"] = fsck_output

    baseline = root / EXPECTED["baseline_object"][0]
    patched = root / EXPECTED["patched_object"][0]
    if baseline.is_file() and patched.is_file():
        baseline_flags = baseline.read_bytes()[FLAGS_OFFSET:FLAGS_OFFSET + 8]
        patched_flags = patched.read_bytes()[FLAGS_OFFSET:FLAGS_OFFSET + 8]
        checks["baseline_flags_hex"] = baseline_flags.hex()
        checks["patched_flags_hex"] = patched_flags.hex()
        if baseline_flags != b"\0" * 8:
            failures.append("baseline object already has a nonzero RBCPR clock flag")
        if patched_flags != struct.pack("<Q", 1 << CLK_IS_CRITICAL_BIT):
            failures.append("patched object does not contain CLK_IS_CRITICAL on RBCPR")

    for field in ("source_head", "config_sha256", "image_sha256", "vmlinux_sha256"):
        checks[f"receipt_{field}"] = build_receipt.get(field)
    checks["receipt_patched_rebuild_identical"] = build_receipt.get(
        "patched_rebuild_identical"
    )
    checks["receipt_source_clean_after"] = build_receipt.get("source_clean_after")
    checks["receipt_clock_file_clean_after"] = build_receipt.get(
        "clock_source_clean_after"
    )
    if build_receipt.get("config_sha256") != CONFIG_SHA256:
        failures.append("build receipt config hash changed")
    if build_receipt.get("image_sha256") != EXPECTED["image"][2]:
        failures.append("build receipt Image hash changed")
    if build_receipt.get("patched_object_sha256") != EXPECTED["patched_object"][2]:
        failures.append("build receipt patched object hash changed")
    if build_receipt.get("baseline_object_sha256") != EXPECTED["baseline_object"][2]:
        failures.append("build receipt baseline object hash changed")
    if not build_receipt.get("patched_rebuild_identical"):
        failures.append("patched object rebuild was not byte-identical")
    if not build_receipt.get("source_clean_after"):
        failures.append("build receipt does not record a clean source tree")
    if not build_receipt.get("clock_source_clean_after"):
        failures.append("build receipt does not record a clean clock source file")

    boot = root / EXPECTED["boot"][0]
    if boot.is_file():
        builder = Path(__file__).with_name("build-boot-larger.py")
        spec = importlib.util.spec_from_file_location("boot_builder", builder)
        if spec is None or spec.loader is None:
            failures.append("cannot load build-boot-larger.py")
        else:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            parsed = module.parse_boot(boot.read_bytes())
            bds_ffs = next(
                item for item in parsed["main_files"] if item["guid"] == module.BDS_GUID
            )
            sections = module.ffs_sections(bds_ffs["full"])
            pe32 = next(item["body"] for item in sections if item["type"] == 0x10)
            checks["bds_pe32_in_boot_sha256"] = hashlib.sha256(pe32).hexdigest()
            if checks["bds_pe32_in_boot_sha256"] != BDS_PE_SHA256:
                failures.append("boot image BDS PE32 hash changed")

    if FLASH_HELPER.is_file():
        helper_hash = sha256(FLASH_HELPER)
        checks["flash_helper_sha256"] = helper_hash
        if helper_hash != HELPER_SHA256:
            failures.append("flash helper hash changed")
        helper_text = FLASH_HELPER.read_text(encoding="utf-8")
        checks["flash_helper_pair_guard"] = (
            "-FlashBoot" in helper_text
            and "-FlashKernelFat" in helper_text
            and "partial flashing is rejected" in helper_text
        )
        if not checks["flash_helper_pair_guard"]:
            failures.append("flash helper does not enforce paired writes")

    checks["not_flashed"] = verification.get("not_tested", {}).get("flashed") is False
    if not checks["not_flashed"]:
        failures.append("verification does not record the unflashed state")

    result = {
        "schema": "samurai-clock-rbcpr-candidate-check-v1",
        "candidate_dir": str(root),
        "passed": not failures,
        "checks": checks,
        "failures": failures,
    }
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    sys.stdout.write(rendered)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
