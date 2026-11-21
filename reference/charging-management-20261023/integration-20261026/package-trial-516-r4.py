"""Pin the independent #516 trial package to the corrected carriers."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


BASE = Path(r"E:\RealmeX2Pro edk2\reference\charging-management-20261023\integration-20261026")
TRIAL = BASE / "trial-516-r4"
OUT = Path(r"E:\edk2-samurai-out\charging-management-20261023")

TRIAL_ID = "charging-integration-516-20261026-08"
TOKEN = "d6c501a47da419a9c5c77736b28616b349c167d655760e4f535aeae07756ae11"
VERSION = "#516 SMP PREEMPT Mon Oct 26 19:29:22 CST 2026"
DEVICE_ROOT = "/root/charging-management-20261023/charging-integration-trial-20261026-08"

IMAGE = Path(
    "/home/cy122/charging-management-20261023/"
    "charging-integration-20261026-01/build/arch/arm64/boot/Image"
)
IMAGE_READ = Path(
    r"\\wsl.localhost\Ubuntu\home\cy122\charging-management-20261023"
    r"\charging-integration-20261026-01\build\arch\arm64\boot\Image"
)
IMAGE_SHA256 = "812f1633e5f92c6ff5e99440a27e03f57d790db6728aee50930719ca5531eddd"
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
    / "charging-integration-20261026-boot-private-06"
    / "boot-charging-dtb-private-06.img"
)
OLD_LOGDUMP = (
    OUT / "route-pm-image506-logdump-private-01/logdump-route506-private.img"
)
NEW_LOGDUMP = (
    OUT
    / "charging-integration-20261026-fat-private-07"
    / "logdump-tcpm-sink507-r2-private.img"
)
DTB = (
    OUT
    / "charging-integration-20261026-fat-private-07"
    / "samurai.dtb"
)
RUNTIME_DTB = (
    OUT
    / "charging-integration-20261026-fat-private-07"
    / "samurai.dtb"
)
BOOT_RECEIPT = (
    OUT / "charging-integration-20261026-boot-private-06/result.json"
)
FAT_RECEIPT = (
    OUT / "charging-integration-20261026-fat-private-07/result.json"
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
    assert manifest["trial_id"] in {"charging-integration-516-20261026-07", TRIAL_ID}

    pin(
        OLD_BOOT,
        "5c8d23d4d5e834593dd3a24537044af8b57e2df53ed3a91fb7880ad7541f8311",
        100663296,
    )
    pin(
        NEW_BOOT,
        "3e64f76801ac26d8ca0654960fc15dd10e627deb13c0831a7392c9846b1ec055",
        100663296,
    )
    pin(
        OLD_LOGDUMP,
        "b29ea41a7a076555f5f6848c9f343dbd8fb0f9271adbd4d3acd4fff9d092b0ff",
        67108864,
    )
    pin(
        NEW_LOGDUMP,
        "4a47fa17ceb51fc0a689726556ca4e9b6d6752902d54f3874c13e5935aa28016",
        67108864,
    )
    pin(
        DTB,
        "b989d5f04dcb3785436db5d5c0ac6524509f0b785df432ca38d658452618da87",
        116012,
    )
    pin(
        RUNTIME_DTB,
        "b989d5f04dcb3785436db5d5c0ac6524509f0b785df432ca38d658452618da87",
        116012,
    )
    pin(IMAGE_READ, IMAGE_SHA256, 59374080)
    pin(MODULE_READ, MODULE_NEW_SHA256, MODULE_NEW_BYTES)
    pin(MODULE_PACKAGE, MODULE_NEW_SHA256, MODULE_NEW_BYTES)
    pin(
        BOOT_RECEIPT,
        "d3b37b1d049eb17cc7e67c075f3c524a8a2539ac77adc5a3895fb2f020e04f84",
        21645,
    )
    pin(
        FAT_RECEIPT,
        "c43c4adb173dd619203c789ea90186def5ccde37502474b65fe82998e727aa10",
        11488,
    )

    boot_receipt = json.loads(BOOT_RECEIPT.read_text())
    assert boot_receipt["passed"] is True
    assert boot_receipt["boot_sha256"] == sha256(NEW_BOOT)
    assert boot_receipt["native_DTB_sha256"] == sha256(DTB)
    assert boot_receipt["new_kernel_size"] == 6680618
    assert boot_receipt["new_used"] == 6686720
    fat_receipt = json.loads(FAT_RECEIPT.read_text())
    assert fat_receipt["passed"] is True
    assert fat_receipt["candidate_fat"]["sha256"] == sha256(NEW_LOGDUMP)
    assert fat_receipt["candidate_fat"]["fsck"]["returncode"] == 0
    assert fat_receipt["candidate_dtb"]["sha256"] == sha256(RUNTIME_DTB)
    assert fat_receipt["unchanged_image"]["sha256"] == IMAGE_SHA256
    assert fat_receipt["fat_integrity"]["only_dtb_file_changed"] is True

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
    manifest["runtime_dtb"] = {
        "path": str(RUNTIME_DTB),
        "fat_path": "::/samurai.dtb",
        "sha256": sha256(RUNTIME_DTB),
        "bytes": RUNTIME_DTB.stat().st_size,
        "fat_receipt_path": str(FAT_RECEIPT),
        "fat_receipt_sha256": sha256(FAT_RECEIPT),
        "features": [
            "typec-supply",
            "usb_in_v_div_16",
            "realme,apsd-handoff-trial",
            "usb-input@1300",
            "connector",
        ],
        "typec_supply_path": (
            "/soc@0/geniqup@8c0000/i2c@884000/charger@5c/typec-supply"
        ),
        "adc_label_path": (
            "/soc@0/spmi@c440000/pmic@2/adc@3100/channel@8/label"
        ),
        "handoff_property_path": (
            "/soc@0/spmi@c440000/pmic@2/typec@1500/"
            "realme,apsd-handoff-trial"
        ),
    }
    manifest["boot_receipt"].update(
        {
            "path": str(BOOT_RECEIPT),
            "sha256": sha256(BOOT_RECEIPT),
            "bytes": BOOT_RECEIPT.stat().st_size,
            "boot_path_suffix": (
                "charging-integration-20261026-boot-private-06/"
                "boot-charging-dtb-private-06.img"
            ),
            "dtb_path_suffix": (
                "charging-integration-20261026-fat-private-07/"
                "samurai.dtb"
            ),
        }
    )
    manifest["postboot"]["version"] = VERSION
    manifest["postboot"]["apsd_adc_proof"] = (
        "direct PM8150B ADC/VBUS sample inside the 4.40-5.50V window; Type-C "
        "partner and TCPM supply present; no full-PD APSD/QC takeover refusal"
    )
    manifest["postboot"]["apsd_vbus_min_uv"] = 4400000
    manifest["postboot"]["apsd_vbus_max_uv"] = 5500000
    manifest["postboot"]["measured_sdp_vbus_min_uv"] = 4511408
    manifest["postboot"]["measured_sdp_vbus_max_uv"] = 4672304
    manifest["postboot"]["typec_supply_property_check"] = (
        "presence of charger@5c/typec-supply"
    )
    manifest["postboot"]["adc_label_property_check"] = (
        "adc@3100/channel@8/label == usb_in_v_div_16"
    )
    manifest["safety"]["rollback_order"] = [
        "boot",
        "logdump",
        "original_main_manifest",
        "original_module",
        "original_service",
        "reboot",
    ]
    manifest["kernel_module"] = {
        "name": "samurai-mp2650",
        "source": "modules/samurai-mp2650.ko",
        "target": (
            "/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/"
            "samurai-charging/samurai-mp2650.ko"
        ),
        "mode": 0o644,
        "old_sha256": MODULE_OLD_SHA256,
        "old_bytes": MODULE_OLD_BYTES,
        "new_sha256": MODULE_NEW_SHA256,
        "new_bytes": MODULE_NEW_BYTES,
    }

    manifest["device_files"].setdefault(
        "/usr/lib/samurai-charging/postboot_audit.py",
        {
            "source": "postboot_audit.py",
            "target": "/usr/lib/samurai-charging/postboot_audit.py",
            "mode": 0o644,
            "sha256": "",
        },
    )
    manifest["device_files"].setdefault(
        "/usr/lib/samurai-charging/trial_autoaudit.py",
        {
            "source": "trial_autoaudit.py",
            "target": "/usr/lib/samurai-charging/trial_autoaudit.py",
            "mode": 0o755,
            "sha256": "",
        },
    )
    for target, (source, mode) in {
        "/usr/lib/samurai-charging/trial_common.py": (TRIAL / "trial_common.py", 0o644),
        "/usr/lib/samurai-charging/trial_guard.py": (TRIAL / "trial_guard.py", 0o755),
        "/usr/lib/samurai-charging/postboot_audit.py": (
            TRIAL / "postboot_audit.py",
            0o644,
        ),
        "/usr/lib/samurai-charging/trial_autoaudit.py": (
            TRIAL / "trial_autoaudit.py",
            0o755,
        ),
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
