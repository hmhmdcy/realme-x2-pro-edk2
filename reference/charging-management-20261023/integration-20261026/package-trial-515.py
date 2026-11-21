"""Pin the independent #515 trial package to the corrected carriers."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


BASE = Path(r"E:\RealmeX2Pro edk2\reference\charging-management-20261023\integration-20261026")
TRIAL = BASE / "trial-515"
OUT = Path(r"E:\edk2-samurai-out\charging-management-20261023")

TRIAL_ID = "charging-integration-515-20261026-05"
TOKEN = "e895945f979b0c3b2d614b6735f2ea54e5a5de882381762c72baafe6c2131a42"
VERSION = "#515 SMP PREEMPT Mon Oct 26 19:00:27 CST 2026"
DEVICE_ROOT = "/root/charging-management-20261023/charging-integration-trial-20261026-05"

IMAGE = Path(
    "/home/cy122/charging-management-20261023/"
    "charging-integration-20261026-01/build/arch/arm64/boot/Image"
)
IMAGE_READ = Path(
    r"\\wsl.localhost\Ubuntu\home\cy122\charging-management-20261023"
    r"\charging-integration-20261026-01\build\arch\arm64\boot\Image"
)
IMAGE_SHA256 = "c20191b2f21c9eb54ee0568a29b3633a334eb2b1c227ef66ed237e528a4e28f0"
OLD_BOOT = OUT / "apsd-image505-boot-private-03/boot-apsd505-private.img"
NEW_BOOT = (
    OUT
    / "charging-integration-20261026-boot-private-04"
    / "boot-tcpm-usb-budget508-private.img"
)
OLD_LOGDUMP = (
    OUT / "route-pm-image506-logdump-private-01/logdump-route506-private.img"
)
NEW_LOGDUMP = (
    OUT
    / "charging-integration-20261026-fat-private-05"
    / "logdump-tcpm-sink507-r2-private.img"
)
DTB = (
    OUT
    / "charging-integration-20261026-dtb-private-01"
    / "samurai-integration509-apsd-private.dtb"
)
BOOT_RECEIPT = (
    OUT / "charging-integration-20261026-boot-private-04/result.json"
)
FAT_RECEIPT = (
    OUT / "charging-integration-20261026-fat-private-05/result.json"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pin(path: Path, digest: str, size: int | None = None) -> None:
    assert path.is_file(), path
    assert sha256(path) == digest, path
    if size is not None:
        assert path.stat().st_size == size, path


def main() -> None:
    manifest_path = TRIAL / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    assert manifest["trial_id"] in {
        "charging-integration-514-20261026-04",
        TRIAL_ID,
    }

    pin(
        OLD_BOOT,
        "5c8d23d4d5e834593dd3a24537044af8b57e2df53ed3a91fb7880ad7541f8311",
        100663296,
    )
    pin(
        NEW_BOOT,
        "8af84ca536c9d4e1f09d7395adb303ba6f2ed6fa9138adef074df95e68e56680",
        100663296,
    )
    pin(
        OLD_LOGDUMP,
        "b29ea41a7a076555f5f6848c9f343dbd8fb0f9271adbd4d3acd4fff9d092b0ff",
        67108864,
    )
    pin(
        NEW_LOGDUMP,
        "365fde1c9155857be4e3b99ffb90b5dfd5edab9ba028c3d319662960e0bf8709",
        67108864,
    )
    pin(
        DTB,
        "9aa3e6fce7833f294a2dd7dc9b8f9d4fc95f3627d0c2386ba2ce183bc4316cd6",
        116966,
    )
    pin(IMAGE_READ, IMAGE_SHA256, 59374080)
    pin(
        BOOT_RECEIPT,
        "ba90e17520e807124ff522339f0f338eae2f1ca94086d734c406b3cf15f33e13",
        33000,
    )
    pin(
        FAT_RECEIPT,
        "212db7a1502f248727fed61429d2f85ba3b8e549f61c0688506e0cbea81b73b2",
        5734,
    )

    boot_receipt = json.loads(BOOT_RECEIPT.read_text())
    assert boot_receipt["passed"] is True
    assert boot_receipt["boot_sha256"] == sha256(NEW_BOOT)
    assert boot_receipt["native_DTB_sha256"] == sha256(DTB)
    assert boot_receipt["new_kernel_size"] == 6680933
    assert boot_receipt["new_used"] == 6686720
    fat_receipt = json.loads(FAT_RECEIPT.read_text())
    assert fat_receipt["passed"] is True
    assert fat_receipt["Image_readback_exact"] is True
    assert fat_receipt["fsck_readonly_passed"] is True
    assert fat_receipt["only_Image_file_changed"] is True
    assert fat_receipt["Image507_R2_sha256"] == IMAGE_SHA256

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
    manifest["boot_receipt"].update(
        {
            "path": str(BOOT_RECEIPT),
            "sha256": sha256(BOOT_RECEIPT),
            "bytes": BOOT_RECEIPT.stat().st_size,
            "boot_path_suffix": (
                "charging-integration-20261026-boot-private-04/"
                "boot-tcpm-usb-budget508-private.img"
            ),
            "dtb_path_suffix": (
                "charging-integration-20261026-dtb-private-01/"
                "samurai-integration509-apsd-private.dtb"
            ),
        }
    )
    manifest["postboot"]["version"] = VERSION
    manifest["postboot"]["apsd_adc_proof"] = (
        "APSD prepare success; Type-C partner and TCPM supply present; no "
        "full-PD APSD/QC takeover refusal"
    )

    for target, (source, mode) in {
        "/usr/lib/samurai-charging/trial_common.py": (TRIAL / "trial_common.py", 0o644),
        "/usr/lib/samurai-charging/trial_guard.py": (TRIAL / "trial_guard.py", 0o755),
        "/etc/init.d/samurai-charging": (TRIAL / "service/samurai-charging", 0o755),
    }.items():
        row = manifest["device_files"][target]
        row["sha256"] = sha256(source)
        row["mode"] = mode

    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
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
