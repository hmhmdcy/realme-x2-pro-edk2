"""Package the integrated Image and measured-VBUS DTB into private carriers.

No device access and no replay: this script only writes new private directories
under /mnt/e/edk2-samurai-out. The 508 board DTB is the already validated
5V-only base with the measured ADC wiring added.
"""
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
    "tcpm-measured-vbus-board-private-01/"
    "samurai-tcpm-measured-vbus-private.dtb"
)
OLD_DTB = ROOT / (
    "tcpm-usb-budget508-dtb-private-01/"
    "samurai-usb-budget508-native-private.dtb"
)
BASE_FAT = ROOT / (
    "route-pm-image506-logdump-private-01/"
    "logdump-route506-private.img"
)
BOOT_OUT = ROOT / "charging-integration-20261026-boot-private-01"
FAT_OUT = ROOT / "charging-integration-20261026-fat-private-01"
IMAGE_SHA = "67fba40cfb690f2853d2f57f46eb2d33850157d7d891d1995adead728c123f4d"
NEW_DTB_SHA = "b9ecb374bb7ba3ddb3490ee9da0ef948cb4c54303b4ed6759820a0aa6a2d6b14"
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


def package_boot():
    boot = load("integration_boot_packager", BOOT_SRC)
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
    boot.HERE = REF / "integration-20261026"
    print(json.dumps({"mode": "boot", "out": str(BOOT_OUT)}), flush=True)
    return boot.execute()


def package_fat():
    fat = load("integration_fat_packager", FAT_SRC)
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
        assert len(image) == 59374080
        return old, image, parsed

    fat.check_local = check_integrated_image
    fat.OLD = BASE_FAT
    fat.IMAGE = IMAGE
    fat.OUT = FAT_OUT
    fat.HERE = REF / "integration-20261026"
    print(json.dumps({"mode": "fat", "out": str(FAT_OUT)}), flush=True)
    return fat.execute()


if __name__ == "__main__":
    if sys.argv[1:] == ["--boot"]:
        raise SystemExit(package_boot())
    if sys.argv[1:] == ["--fat"]:
        raise SystemExit(package_fat())
    raise SystemExit("Use --boot or --fat")
