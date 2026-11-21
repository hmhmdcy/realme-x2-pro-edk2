"""Pin the EUD-route-enabled #517 trial package without device IO."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


BASE = Path(
    r"E:\RealmeX2Pro edk2\reference\charging-management-20261023"
    r"\integration-20261026"
)
TRIAL = BASE / "trial-517-r7"
OUT = Path(r"E:\edk2-samurai-out\charging-management-20261023")

TRIAL_ID = "charging-integration-517-20261027-01"
TOKEN = "891d451473d242d49473813ef34f5b3f9c613ecae331f499a924527934f5c1d3"
VERSION = "#517 SMP PREEMPT Tue Oct 27 00:17:40 CST 2026"
DEVICE_ROOT = (
    "/root/charging-management-20261023/"
    "charging-integration-trial-20261027-01"
)

IMAGE = Path(
    "/home/cy122/charging-management-20261023/"
    "charging-integration-20261026-01/build-r7/Image-r7-k517.img"
)
IMAGE_READ = Path(
    r"\\wsl.localhost\Ubuntu\home\cy122\charging-management-20261023"
    r"\charging-integration-20261026-01\build-r7\Image-r7-k517.img"
)
IMAGE_SHA256 = "6e45cbb780b7de690f714a17b54524369b630eccff8ee773acbbb38a59f90f2f"

MODULE_READ = Path(
    r"\\wsl.localhost\Ubuntu\home\cy122\charging-management-20261023"
    r"\charging-integration-20261026-01\r8-module\final-build"
    r"\drivers\power\supply\samurai-mp2650.ko"
)
MODULE_PACKAGE = TRIAL / "modules/samurai-mp2650.ko"
MODULE_OLD_SHA256 = (
    "bef4dba73e1244fec4c89f2d5b47ac6b1483384c1f64aa1d589de792d2e97d6f"
)
MODULE_OLD_BYTES = 156784
MODULE_NEW_SHA256 = (
    "04da6a7bf492e44d6afa533816e662d54b5a5f0391f4fe0e5e6e7f8555cedf69"
)
MODULE_NEW_BYTES = 164360

OLD_BOOT = OUT / "apsd-image505-boot-private-03/boot-apsd505-private.img"
NEW_BOOT = (
    OUT
    / "charging-integration-20261027-boot-private-01"
    / "boot-eud-off-route-private-r7.img"
)
OLD_LOGDUMP = (
    OUT / "route-pm-image506-logdump-private-01/logdump-route506-private.img"
)
NEW_LOGDUMP = (
    OUT
    / "charging-integration-20261027-fat-private-01"
    / "logdump-tcpm-sink507-r2-private.img"
)
DTB = (
    OUT
    / "charging-integration-20261026-dtb-private-02"
    / "samurai-eud-off-route-okay.dtb"
)
RUNTIME_DTB = DTB
BOOT_RECEIPT = (
    OUT / "charging-integration-20261027-boot-private-01/result.json"
)
FAT_RECEIPT = (
    OUT / "charging-integration-20261027-fat-private-01/result.json"
)

REPLACEMENTS = {
    "charging-integration-516-20261026-10": TRIAL_ID,
    "charging-integration-trial-20261026-10": (
        "charging-integration-trial-20261027-01"
    ),
    "#516 SMP PREEMPT Mon Oct 26 19:29:22 CST 2026": VERSION,
    "812f1633e5f92c6ff5e99440a27e03f57d790db6728aee50930719ca5531eddd": (
        IMAGE_SHA256
    ),
    "dc9e01393c1f3e98babc4020c810b72f63107bebeb0ff31c77683e227011d416": (
        "d884075a04d00112c95d0d3215ae342d43fb94d03a19b7753bf3f6deee2bbb43"
    ),
    "d73da9329ba70afd869805df0a6b8a86aa53870cd2c8ddaaa57ebcbe479b0e6c": (
        "d0dad3c362529d2a5c00e37b4ba4349cb591318b0dd3789eb100a7e15a19e420"
    ),
    "93102cd90a1b3223cc5dea65f8245b7422e50912c9ee683b50d37dd0e2f931b0": (
        "9314c3f2b0cb7c971342cfcd238e96862f7ee83e34ea87c3fd465176cafcf95d"
    ),
    "bf3607ba6389474785229dd01579212f7bba27a9aec249dabd1b32441c16f1a2": TOKEN,
    "charging-integration-20261026-boot-private-07": (
        "charging-integration-20261027-boot-private-01"
    ),
    "boot-eud-off-route-private-07.img": "boot-eud-off-route-private-r7.img",
    "charging-integration-20261026-fat-private-08": (
        "charging-integration-20261027-fat-private-01"
    ),
    "logdump-eud-off-private-08.img": "logdump-tcpm-sink507-r2-private.img",
    "charging-integration-20261026-01/build/arch/arm64/boot/Image": (
        "charging-integration-20261026-01/build-r7/Image-r7-k517.img"
    ),
    "trial-516-r6": "trial-517-r7",
    "#516": "#517",
    "attempt 6": "attempt 7",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pin(path: Path, digest: str, size: int | None = None) -> None:
    assert path.is_file(), path
    assert sha256(path) == digest, path
    if size is not None:
        assert path.stat().st_size == size, path


def update_text_files() -> None:
    for path in TRIAL.rglob("*"):
        if not path.is_file() or "modules" in path.relative_to(TRIAL).parts:
            continue
        if path.name in {
            "manifest.json",
            "package-result.json",
            "SHA256SUMS",
            "SHA256SUMS.verify.txt",
        }:
            continue
        if path.name.startswith("test-run-") or path.name.startswith("test-results"):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        updated = text
        for old, new in REPLACEMENTS.items():
            updated = updated.replace(old, new)
        if updated != text or b"\r\n" in path.read_bytes():
            path.write_text(updated, encoding="utf-8", newline="\n")


def main() -> None:
    update_text_files()

    manifest_path = TRIAL / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    assert manifest["trial_id"] in {
        "charging-integration-516-20261026-10",
        TRIAL_ID,
    }

    pin(
        OLD_BOOT,
        "5c8d23d4d5e834593dd3a24537044af8b57e2df53ed3a91fb7880ad7541f8311",
        100663296,
    )
    pin(
        NEW_BOOT,
        "13c98860646fa80241a0a042e17781fceb7873f13263c69433839fd11ab9f756",
        100663296,
    )
    pin(
        OLD_LOGDUMP,
        "b29ea41a7a076555f5f6848c9f343dbd8fb0f9271adbd4d3acd4fff9d092b0ff",
        67108864,
    )
    pin(
        NEW_LOGDUMP,
        "d884075a04d00112c95d0d3215ae342d43fb94d03a19b7753bf3f6deee2bbb43",
        67108864,
    )
    pin(
        DTB,
        "d7d8a7da7a3fc68b37faceda0fd7c7f506fbbd17b7a510c15cb978b9160acf1b",
        116962,
    )
    pin(IMAGE_READ, IMAGE_SHA256, 59374080)
    pin(MODULE_READ, MODULE_NEW_SHA256, MODULE_NEW_BYTES)
    pin(MODULE_PACKAGE, MODULE_NEW_SHA256, MODULE_NEW_BYTES)
    pin(
        BOOT_RECEIPT,
        "9314c3f2b0cb7c971342cfcd238e96862f7ee83e34ea87c3fd465176cafcf95d",
        20180,
    )
    pin(
        FAT_RECEIPT,
        "d0dad3c362529d2a5c00e37b4ba4349cb591318b0dd3789eb100a7e15a19e420",
        5757,
    )

    boot_receipt = json.loads(BOOT_RECEIPT.read_text())
    assert boot_receipt["passed"] is True
    assert boot_receipt["boot_sha256"] == sha256(NEW_BOOT)
    assert boot_receipt["native_DTB_sha256"] == sha256(DTB)
    assert boot_receipt["fat_Image_sha256"] == IMAGE_SHA256

    fat_receipt = json.loads(FAT_RECEIPT.read_text())
    assert fat_receipt["passed"] is True
    assert fat_receipt["candidate"]["sha256"] == sha256(NEW_LOGDUMP)
    assert fat_receipt["Image507_R2_sha256"] == IMAGE_SHA256
    assert fat_receipt["native_DTB_untouched"] is True
    assert fat_receipt["fsck_readonly_passed"] is True

    manifest.update(
        {
            "trial_id": TRIAL_ID,
            "token": TOKEN,
            "kernel_version": VERSION,
            "device_root": DEVICE_ROOT,
        }
    )
    manifest["carriers"]["boot"].update(
        {
            "new": sha256(NEW_BOOT),
            "new_path": str(NEW_BOOT),
            "old": sha256(OLD_BOOT),
            "old_path": str(OLD_BOOT),
        }
    )
    manifest["carriers"]["logdump"].update(
        {
            "new": sha256(NEW_LOGDUMP),
            "new_path": str(NEW_LOGDUMP),
            "old": sha256(OLD_LOGDUMP),
            "old_path": str(OLD_LOGDUMP),
        }
    )
    manifest["image"].update(
        {
            "path": str(IMAGE),
            "sha256": sha256(IMAGE_READ),
            "bytes": IMAGE_READ.stat().st_size,
            "fat_receipt_path": str(FAT_RECEIPT),
            "fat_receipt_sha256": sha256(FAT_RECEIPT),
        }
    )
    manifest["dtb"].update(
        {
            "path": str(DTB),
            "sha256": sha256(DTB),
            "bytes": DTB.stat().st_size,
        }
    )
    manifest["runtime_dtb"].update(
        {
            "path": str(RUNTIME_DTB),
            "sha256": sha256(RUNTIME_DTB),
            "bytes": RUNTIME_DTB.stat().st_size,
            "fat_receipt_path": str(FAT_RECEIPT),
            "fat_receipt_sha256": sha256(FAT_RECEIPT),
        }
    )
    manifest["boot_receipt"].update(
        {
            "path": str(BOOT_RECEIPT),
            "sha256": sha256(BOOT_RECEIPT),
            "bytes": BOOT_RECEIPT.stat().st_size,
            "boot_path_suffix": (
                "charging-integration-20261027-boot-private-01/"
                "boot-eud-off-route-private-r7.img"
            ),
            "dtb_path_suffix": (
                "charging-integration-20261026-dtb-private-02/"
                "samurai-eud-off-route-okay.dtb"
            ),
        }
    )
    manifest["postboot"]["version"] = VERSION

    for target, source, mode in (
        (
            "/etc/init.d/samurai-charging",
            TRIAL / "service/samurai-charging",
            0o755,
        ),
        (
            "/usr/lib/samurai-charging/postboot_audit.py",
            TRIAL / "postboot_audit.py",
            0o644,
        ),
        (
            "/usr/lib/samurai-charging/trial_autoaudit.py",
            TRIAL / "trial_autoaudit.py",
            0o755,
        ),
        (
            "/usr/lib/samurai-charging/trial_common.py",
            TRIAL / "trial_common.py",
            0o644,
        ),
        (
            "/usr/lib/samurai-charging/trial_guard.py",
            TRIAL / "trial_guard.py",
            0o755,
        ),
    ):
        row = manifest["device_files"][target]
        row["sha256"] = sha256(source)
        row["mode"] = mode

    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        newline="\n",
    )

    operator = TRIAL / "fastboot_operator.ps1"
    operator_text = operator.read_text()
    if IMAGE_SHA256 not in operator_text or "production #517 Image" not in operator_text:
        raise SystemExit("unexpected fastboot operator production pins")

    for stale in (
        TRIAL / "test-run-r6-windows.log",
        TRIAL / "test-results.json",
        TRIAL / "test-results-linux.json",
    ):
        stale.unlink(missing_ok=True)

    print(
        json.dumps(
            {
                "trial_id": TRIAL_ID,
                "manifest": str(manifest_path),
                "manifest_sha256": sha256(manifest_path),
                "image": sha256(IMAGE_READ),
                "boot": sha256(NEW_BOOT),
                "logdump": sha256(NEW_LOGDUMP),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
