#!/usr/bin/env python3
"""Verify the RMX1931 private-status removal image and paired FAT."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys


EXPECTED = {
    "image": (
        59308544,
        "f8d8962197827dafbe50e551f5df03391c43ec0269449fa87b833e57799656a5",
    ),
    "baseline_image": (
        59308544,
        "aa6c4b6b43ec45f4c41d3d420b980e35876860537cb6f2cb96ec5063aab8432a",
    ),
    "dtb": (
        114656,
        "b244b3f10a14811dca2e808efa8c840f432cac69020e66b60eba97d02794a18e",
    ),
    "boot": (
        100663296,
        "5b4dd4871f6856710ff58e722ffd8b2c30d04baf0104b262adcb02e46a7651bf",
    ),
    "kernel_fat": (
        67108864,
        "1f4bbb302a62d1f8a950994ac93b00ca194a41c768d4d11b1b97c69f5702574b",
    ),
    "baseline_fat": (
        67108864,
        "c99c690ee923238b0954975682c0e40ce99ae63afd048d40b5059fea70e5862e",
    ),
}

RELEASE = b"7.3.1-rmx1931-samurai-v731"
REMOVED_MARKERS = (
    b"watchdog_stops",
    b"starts=%u stops=%u",
)
RETAINED_MARKERS = (
    b"AW8697 id=97 standby",
    b"MAX98937 revision=%02x channel=%u",
    b"realme,samurai-sensor-power",
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def run(argv: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(argv, capture_output=True, check=False)


def add_check(
    checks: list[dict],
    name: str,
    passed: bool,
    detail: str,
) -> None:
    checks.append({
        "name": name,
        "passed": bool(passed),
        "detail": detail,
    })


def check_file(
    checks: list[dict],
    name: str,
    path: Path,
    expected_size: int | None = None,
    expected_hash: str | None = None,
) -> bool:
    if not path.is_file():
        add_check(checks, f"{name}_exists", False, str(path))
        return False
    add_check(checks, f"{name}_exists", True, str(path))
    if expected_size is not None:
        actual_size = path.stat().st_size
        add_check(
            checks,
            f"{name}_size",
            actual_size == expected_size,
            f"{actual_size} (expected {expected_size})",
        )
    if expected_hash is not None:
        actual = sha256_file(path)
        add_check(
            checks,
            f"{name}_sha256",
            actual == expected_hash,
            f"{actual} (expected {expected_hash})",
        )
    return True


def check_image(path: Path, checks: list[dict]) -> None:
    data = path.read_bytes()
    add_check(
        checks,
        "image_release",
        RELEASE in data,
        RELEASE.decode("ascii"),
    )
    add_check(
        checks,
        "image_release_has_no_dirty_suffix",
        RELEASE + b"+" not in data,
        "no trailing plus in the version strings",
    )
    for marker in REMOVED_MARKERS:
        add_check(
            checks,
            f"image_removed_{marker.decode('ascii', 'replace')}",
            marker not in data,
            marker.decode("ascii", "replace"),
        )
    for marker in RETAINED_MARKERS:
        add_check(
            checks,
            f"image_retained_{marker.decode('ascii', 'replace')}",
            marker in data,
            marker.decode("ascii", "replace"),
        )


def check_fat(path: Path, checks: list[dict]) -> None:
    mtype = shutil.which("mtype")
    if mtype is None:
        add_check(
            checks,
            "mtools_available",
            False,
            "mtype not found; run this verifier in WSL",
        )
        return
    add_check(checks, "mtools_available", True, mtype)

    for name, expected in (
        ("Image", EXPECTED["image"][1]),
        ("samurai.dtb", EXPECTED["dtb"][1]),
    ):
        result = run([mtype, "-i", str(path), f"::/{name}"])
        actual = sha256_bytes(result.stdout) if result.returncode == 0 else ""
        add_check(
            checks,
            f"fat_{name}_sha256",
            result.returncode == 0 and actual == expected,
            actual or result.stderr.decode("utf-8", "replace").strip(),
        )

    fsck = shutil.which("fsck.vfat")
    if fsck is None:
        add_check(
            checks,
            "fat_fsck_available",
            False,
            "fsck.vfat not found",
        )
        return
    result = run([fsck, "-n", str(path)])
    add_check(
        checks,
        "fat_fsck_clean",
        result.returncode == 0,
        result.stdout.decode("utf-8", "replace").strip(),
    )


def check_source_evidence(
    repo: Path,
    checks: list[dict],
) -> None:
    patch = repo / "linux-port/patches/v7.3.1/0004-samurai-remove-private-status-sysfs.patch"
    add_check(
        checks,
        "removal_patch_sha256",
        patch.is_file()
        and sha256_file(patch)
        == "f69ffecd482d11c19f25f074ed5d2ccc48ac765acbf22c54956701bdd0497a5c",
        str(patch),
    )
    audit = repo / "linux-port/scripts/audit-thin-private-layer.py"
    add_check(
        checks,
        "thin_audit_sha256",
        audit.is_file()
        and sha256_file(audit)
        == "143cc2d2146981232a74999186bad5d60cd415ec411da3ae9f0e04b71fb24c6a",
        str(audit),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path(__file__).resolve().parents[2],
    )
    parser.add_argument(
        "--candidate-dir",
        type=Path,
        default=Path(
            "/mnt/e/edk2-samurai-out/standard-arm64-v731/"
            "thin-private-final-20261109"
        ),
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    repo = args.repo.resolve()
    candidate = args.candidate_dir.resolve()
    output = args.output or candidate / "verification.json"
    checks: list[dict] = []

    paths = {
        "image": candidate / "Image-v731-thin-private",
        "baseline_image": candidate / "Image-baseline-aa6c4b6b",
        "dtb": candidate / "sm8150-samurai-v731-flash-led-v4l2.dtb",
        "boot": candidate / "boot-eud-production-off.img",
        "kernel_fat": candidate / "recovery-kernel-fat-thin-private-final.img",
        "baseline_fat": candidate / "recovery-kernel-fat-baseline.img",
        "rollback_boot": candidate / "rollback/boot-baseline-5b4dd487.img",
        "rollback_fat": (
            candidate / "rollback/recovery-kernel-fat-baseline-c99c690e.img"
        ),
        "build_result": candidate / "build-result.json",
    }

    for name in (
        "image",
        "baseline_image",
        "dtb",
        "boot",
        "kernel_fat",
        "baseline_fat",
    ):
        size, digest = EXPECTED[name]
        check_file(checks, name, paths[name], size, digest)

    check_file(
        checks,
        "rollback_boot",
        paths["rollback_boot"],
        EXPECTED["boot"][0],
        EXPECTED["boot"][1],
    )
    check_file(
        checks,
        "rollback_fat",
        paths["rollback_fat"],
        EXPECTED["baseline_fat"][0],
        EXPECTED["baseline_fat"][1],
    )

    if paths["image"].is_file():
        check_image(paths["image"], checks)
        actual = sha256_file(paths["image"])
        add_check(
            checks,
            "image_is_new_candidate",
            actual == EXPECTED["image"][1]
            and actual != EXPECTED["baseline_image"][1],
            actual,
        )
    if paths["kernel_fat"].is_file():
        check_fat(paths["kernel_fat"], checks)
    if paths["boot"].is_file() and paths["baseline_image"].is_file():
        add_check(
            checks,
            "boot_carrier_unchanged",
            sha256_file(paths["boot"]) == EXPECTED["boot"][1],
            "the boot carrier stays at the camera baseline",
        )

    check_source_evidence(repo, checks)
    if paths["build_result"].is_file():
        result = json.loads(paths["build_result"].read_text(encoding="utf-8"))
        add_check(
            checks,
            "build_result_release",
            result.get("release") == RELEASE.decode("ascii"),
            str(result.get("release")),
        )
        add_check(
            checks,
            "build_result_image",
            result.get("image", {}).get("sha256") == EXPECTED["image"][1],
            str(result.get("image", {}).get("sha256")),
        )
    else:
        add_check(checks, "build_result_exists", False, str(paths["build_result"]))

    passed = bool(checks) and all(item["passed"] for item in checks)
    report = {
        "schema": "samurai-thin-private-candidate-verifier-v1",
        "passed": passed,
        "candidate_dir": str(candidate),
        "release": RELEASE.decode("ascii"),
        "checks": checks,
        "failures": [item for item in checks if not item["passed"]],
        "scope": (
            "Offline artifact, release, removed-string, FAT readback and "
            "rollback checks only. It does not prove that the image boots, "
            "that the drivers probe, or that the deleted sysfs nodes disappeared "
            "from a running kernel."
        ),
        "candidate_basis": (
            "The currently deployed flash-LED/V4L2 FAT and boot carrier are "
            "held byte-identical except for replacing FAT /Image with the "
            "private-status-removal Image."
        ),
    }
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
