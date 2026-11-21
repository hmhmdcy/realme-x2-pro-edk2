"""Package the #518 Image with the proven EUD-off boot and DTB carriers."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys

sys.dont_write_bytecode = True
if sys.flags.optimize:
    raise RuntimeError("Non-optimized interpreter required")

ROOT = Path("/mnt/e/edk2-samurai-out/charging-management-20261023")
REF = Path("/mnt/e/RealmeX2Pro edk2/reference/charging-management-20261023")
BOOT_SRC = Path(
    "/mnt/e/RealmeX2Pro edk2/reference/charging-oem-audit-20261023/"
    "tcpm-usb-budget-candidate/package-boot.py"
)
FAT_SRC = Path(
    "/mnt/e/RealmeX2Pro edk2/reference/charging-oem-audit-20261023/"
    "tcpm-sink-shutdown-candidate/package-logdump.py"
)
IMAGE = Path(
    "/home/cy122/charging-management-20261023/"
    "charging-integration-20261026-01/build-r8/Image-r8-k518.img"
)
NEW_DTB = ROOT / (
    "charging-integration-20261026-dtb-private-02/"
    "samurai-eud-off-route-okay.dtb"
)
OLD_DTB = ROOT / (
    "tcpm-usb-budget508-dtb-private-01/"
    "samurai-usb-budget508-native-private.dtb"
)
BASE_FAT = ROOT / (
    "charging-integration-20261027-fat-private-01/"
    "logdump-tcpm-sink507-r2-private.img"
)
BOOT_OUT = ROOT / "charging-integration-20261027-boot-private-02"
FAT_OUT = ROOT / "charging-integration-20261027-fat-private-02"
WORK = REF / "integration-20261027-r14"

IMAGE_SHA = "3b6ac0f7f2ebf0ce027a8cf63ea65e5b44960a3943edd61504c807b171770f6b"
IMAGE_BYTES = 59374080
RELEASE = "7.3.0-rc6-rmx1931-samurai-k363"
KERNEL_VERSION = "#518 SMP PREEMPT Tue Oct 27 04:21:36 CST 2026"
NEW_DTB_SHA = "d7d8a7da7a3fc68b37faceda0fd7c7f506fbbd17b7a510c15cb978b9160acf1b"
OLD_DTB_SHA = "0ae7ade264e4d27c91861c2e87bb476f2237100f1d27ea8672cbbdba9f184f57"
BASE_FAT_SHA = "d884075a04d00112c95d0d3215ae342d43fb94d03a19b7753bf3f6deee2bbb43"
BASE_IMAGE_SHA = "6e45cbb780b7de690f714a17b54524369b630eccff8ee773acbbb38a59f90f2f"
BASE_DTB_IN_FAT_SHA = (
    "d7d8a7da7a3fc68b37faceda0fd7c7f506fbbd17b7a510c15cb978b9160acf1b"
)
BQ_SYMBOL = "bq27xxx_battery_set_status_override"
BUILD_ROOT = Path(
    "/home/cy122/charging-management-20261023/"
    "charging-integration-20261026-01/build"
)
BUILD_LOG = Path(
    "/home/cy122/charging-management-20261023/"
    "charging-integration-20261026-01/"
    "Image-build-status-precharge-r8-final.log"
)


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def bq_export_rows() -> list[str]:
    rows = []
    needle = f"\t{BQ_SYMBOL}\tvmlinux\tEXPORT_SYMBOL_GPL"
    for line in (BUILD_ROOT / "vmlinux.symvers").read_text().splitlines():
        if needle in line:
            rows.append(line)
    return rows


def write_image_provenance() -> None:
    image = IMAGE.read_bytes()
    assert len(image) == IMAGE_BYTES
    assert hashlib.sha256(image).hexdigest() == IMAGE_SHA
    assert KERNEL_VERSION.encode() in image
    assert RELEASE.encode() in image
    export_rows = bq_export_rows()
    assert len(export_rows) == 1
    payload = {
        "passed": True,
        "actual_phone_booted": False,
        "device_accessed": False,
        "installed": False,
        "boot_partition_or_fat_generated": False,
        "image": {
            "path": str(IMAGE),
            "sha256": IMAGE_SHA,
            "bytes": IMAGE_BYTES,
            "kernel_version": KERNEL_VERSION,
            "release": RELEASE,
            "build_log": str(BUILD_LOG),
            "bq_full_status_export": BQ_SYMBOL,
            "bq_full_status_export_owner": "vmlinux",
            "bq_full_status_export_type": "EXPORT_SYMBOL_GPL",
            "apsd_vbus_min_uv": 4400000,
            "apsd_vbus_max_uv": 5500000,
            "measured_sdp_vbus_min_uv": 4511408,
            "measured_sdp_vbus_max_uv": 4672304,
        },
        "build": {
            "Image_sha256": IMAGE_SHA,
            "Image_bytes": IMAGE_BYTES,
            "release": RELEASE,
            "kernel_version": KERNEL_VERSION,
            "version_verified_in_image": True,
            "bq_full_status_export_rows": len(export_rows),
            "strict_object_build": True,
        },
    }
    WORK.mkdir(parents=True, exist_ok=False)
    (WORK / "image-build-result.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )


def package_boot() -> int:
    boot = load("integration_boot_packager_r14", BOOT_SRC)
    assert sha(IMAGE) == IMAGE_SHA
    assert sha(NEW_DTB) == NEW_DTB_SHA
    assert sha(OLD_DTB) == OLD_DTB_SHA
    original_check = boot.check_local

    def checked_with_new_dtb():
        saved = boot.DTB
        boot.DTB = OLD_DTB
        old = original_check()
        boot.DTB = saved
        assert sha(NEW_DTB) == NEW_DTB_SHA
        return old

    boot.check_local = checked_with_new_dtb
    boot.DTB = NEW_DTB
    boot.OUT = BOOT_OUT
    boot.HERE = WORK
    print(json.dumps({"mode": "boot", "out": str(BOOT_OUT)}), flush=True)
    return boot.execute()


def package_fat() -> int:
    fat = load("integration_fat_packager_r14", FAT_SRC)
    assert sha(IMAGE) == IMAGE_SHA
    assert sha(BASE_FAT) == BASE_FAT_SHA

    def check_integrated_image():
        old = fat.pinned(fat.OLD, BASE_FAT_SHA)
        parsed = fat.parse_fat(old)
        assert parsed["files"]["Image"]["sha256"] == BASE_IMAGE_SHA
        assert parsed["files"]["SAMURAI.DTB"]["sha256"] == BASE_DTB_IN_FAT_SHA
        for path, digest in fat.TOOLS.values():
            fat.pinned(Path(path), digest)
        image = fat.pinned(fat.IMAGE, IMAGE_SHA)
        assert len(image) == IMAGE_BYTES
        return old, image, parsed

    fat.check_local = check_integrated_image
    fat.OLD = BASE_FAT
    fat.IMAGE = IMAGE
    fat.OUT = FAT_OUT
    fat.HERE = WORK
    print(json.dumps({"mode": "fat", "out": str(FAT_OUT)}), flush=True)
    return fat.execute()


if __name__ == "__main__":
    if sys.argv[1:] == ["--provenance"]:
        write_image_provenance()
        raise SystemExit(0)
    if sys.argv[1:] == ["--boot"]:
        assert (WORK / "image-build-result.json").is_file()
        raise SystemExit(package_boot())
    if sys.argv[1:] == ["--fat"]:
        assert (WORK / "image-build-result.json").is_file()
        raise SystemExit(package_fat())
    raise SystemExit("Use --provenance, --boot, or --fat")
