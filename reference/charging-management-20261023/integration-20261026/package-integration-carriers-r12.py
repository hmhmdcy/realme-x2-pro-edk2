"""Package the measured-VBUS #516 Image and APSD DTB into fresh carriers."""
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
    "charging-integration-20261026-01/build/arch/arm64/boot/Image"
)
NEW_DTB = ROOT / (
    "charging-integration-20261026-dtb-private-01/"
    "samurai-integration509-apsd-private.dtb"
)
OLD_DTB = ROOT / (
    "tcpm-usb-budget508-dtb-private-01/"
    "samurai-usb-budget508-native-private.dtb"
)
BASE_FAT = ROOT / (
    "route-pm-image506-logdump-private-01/"
    "logdump-route506-private.img"
)
BOOT_OUT = ROOT / "charging-integration-20261026-boot-private-05"
FAT_OUT = ROOT / "charging-integration-20261026-fat-private-06"
WORK = REF / "integration-20261026-r12"

IMAGE_SHA = "812f1633e5f92c6ff5e99440a27e03f57d790db6728aee50930719ca5531eddd"
IMAGE_BYTES = 59374080
RELEASE = "7.3.0-rc6-rmx1931-samurai-k363+"
KERNEL_VERSION = "#516 SMP PREEMPT Mon Oct 26 19:29:22 CST 2026"
NEW_DTB_SHA = "9aa3e6fce7833f294a2dd7dc9b8f9d4fc95f3627d0c2386ba2ce183bc4316cd6"
OLD_DTB_SHA = "0ae7ade264e4d27c91861c2e87bb476f2237100f1d27ea8672cbbdba9f184f57"
BASE_FAT_SHA = "b29ea41a7a076555f5f6848c9f343dbd8fb0f9271adbd4d3acd4fff9d092b0ff"
BASE_IMAGE_SHA = "c03cf30de35a3a621dff2568805e098656d499de45d5ce9af39c802e74356c24"
BASE_DTB_IN_FAT_SHA = "a82383fa30609bb5e1400f8af12055abdbca7373734c983549d9f437afae2cc5"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_image_provenance():
    image = IMAGE.read_bytes()
    assert len(image) == IMAGE_BYTES
    assert hashlib.sha256(image).hexdigest() == IMAGE_SHA
    assert KERNEL_VERSION.encode() in image
    assert RELEASE.encode() in image
    payload = {
        "passed": True,
        "actual_phone_booted": False,
        "device_accessed": False,
        "installed": False,
        "boot_partition_or_fat_generated": True,
        "image": {
            "path": str(IMAGE),
            "sha256": IMAGE_SHA,
            "bytes": IMAGE_BYTES,
            "kernel_version": KERNEL_VERSION,
            "release": RELEASE,
            "build_log": str(
                Path("/home/cy122/charging-management-20261023/"
                     "charging-integration-20261026-01/Image-build-r12-final.log")
            ),
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
            "apsd_vbus_min_uv": 4400000,
            "strict_object_build": True,
        },
    }
    WORK.mkdir(parents=True, exist_ok=False)
    (WORK / "image-build-result.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )


def package_boot():
    boot = load("integration_boot_packager_r11", BOOT_SRC)
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


def package_fat():
    fat = load("integration_fat_packager_r11", FAT_SRC)
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
