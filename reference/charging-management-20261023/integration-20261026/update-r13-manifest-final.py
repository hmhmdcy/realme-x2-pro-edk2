from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(r"E:\RealmeX2Pro edk2\reference\charging-management-20261023\integration-20261026")
TRIAL = ROOT / "trial-517-r9-status-precharge"
OUT = Path(r"E:\edk2-samurai-out\charging-management-20261023")
FAT = OUT / "charging-integration-20261027-fat-private-10"
BOOT = OUT / "charging-integration-20261027-boot-private-12"
BUILD = Path(r"\\wsl.localhost\Ubuntu\home\cy122\charging-management-20261023\charging-integration-20261026-01\build")
KERNEL_VERSION = "#528 SMP PREEMPT Tue Oct 27 08:49:26 CST 2026"
RELEASE = "7.3.0-rc6-rmx1931-samurai-k363+"
BUILD_PINS = {
    "Image": ("8a4aea91b809423561ffd7cb9bf6f651dd01c1952815e0fce467ce860d944312", 59374080),
    "vmlinux": ("3137c48b553c7bde47d73f70f91c0a8dd4d83e3f77718ecaf55e7adb4d81cdb1", 191012264),
    "System.map": ("bbe71ef44f77782e7f50ebdaad37ee8ddd1f86bcaefb95f39972bf9348f4e717", 9023851),
    "Module.symvers": ("30f1b6a7f36ec07d857415129731c8e2a7640a2cbc26242dd00fcfa6a2782d39", 876635),
}


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    manifest_path = TRIAL / "manifest.json"
    manifest = json.loads(manifest_path.read_text())

    boot_receipt = BOOT / "result.json"
    boot_image = BOOT / "boot-eud-off-route-private-r16.img"
    fat_receipt = FAT / "result.json"
    fat_image = FAT / "logdump-mp2650-r13-private.img"

    manifest["boot_receipt"].update(
        path=str(boot_receipt),
        bytes=boot_receipt.stat().st_size,
        sha256=sha(boot_receipt),
        boot_path_suffix="charging-management-20261023/charging-integration-20261027-boot-private-12/boot-eud-off-route-private-r16.img",
    )
    manifest["carriers"]["boot"].update(
        new=sha(boot_image),
        new_path=str(boot_image),
    )
    manifest["carriers"]["logdump"].update(
        new=sha(fat_image),
        new_path=str(fat_image),
    )
    manifest["image"].update(
        sha256=BUILD_PINS["Image"][0],
        bytes=BUILD_PINS["Image"][1],
        fat_receipt_path=str(fat_receipt),
        fat_receipt_sha256=sha(fat_receipt),
    )
    module_path = TRIAL / manifest["kernel_module"]["source"]
    manifest["kernel_module"]["new_sha256"] = sha(module_path)
    manifest["kernel_module"]["new_bytes"] = module_path.stat().st_size
    module_target = (
        "/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/"
        "samurai-charging/samurai-mp2650.ko"
    )
    manifest["kernel_module"]["target"] = module_target
    for row in manifest.get("auxiliary_kernel_modules", []):
        row["target"] = row["target"].replace(
            "samurai-k363/extra/", "samurai-k363+/extra/"
        )
        source = TRIAL / row["source"]
        row["new_sha256"] = sha(source)
        row["new_bytes"] = source.stat().st_size
    manifest["kernel_version"] = KERNEL_VERSION
    manifest["release"] = RELEASE
    manifest["auto_rollback_on_attention"] = False
    manifest["postboot"]["version"] = KERNEL_VERSION
    manifest["runtime_dtb"]["fat_receipt_path"] = str(fat_receipt)
    manifest["runtime_dtb"]["fat_receipt_sha256"] = sha(fat_receipt)

    provenance = manifest["image_provenance"]
    provenance["kernel_build_label"] = "#528"
    provenance["kernel_version"] = KERNEL_VERSION
    provenance["kernel_version_suffix"] = "SMP PREEMPT Tue Oct 27 08:49:26 CST 2026"
    provenance["kernel_release"] = RELEASE
    provenance["kernel_release_base"] = RELEASE
    for key, name in (
        ("built_image", "Image"),
        ("selected_image", "Image"),
        ("system_map", "System.map"),
        ("vmlinux", "vmlinux"),
    ):
        provenance[key]["sha256"], provenance[key]["bytes"] = BUILD_PINS[name]
    provenance["bq27xxx_export"]["module_symvers_sha256"] = BUILD_PINS["Module.symvers"][0]
    provenance["bq27xxx_export"]["module_symvers_bytes"] = BUILD_PINS["Module.symvers"][1]

    for target, row in manifest["device_files"].items():
        row["sha256"] = sha(TRIAL / row["source"])

    snapshot_root = TRIAL / "source-snapshot"
    manifest["source_snapshot"] = {
        path.relative_to(TRIAL).as_posix(): sha(path)
        for path in sorted(snapshot_root.rglob("*"))
        if path.is_file()
    }

    manifest_path.write_bytes((json.dumps(manifest, indent=2) + "\n").encode())
    print(json.dumps({
        "manifest": str(manifest_path),
        "manifest_sha256": sha(manifest_path),
        "image": manifest["image"]["sha256"],
        "boot": manifest["carriers"]["boot"]["new"],
        "logdump": manifest["carriers"]["logdump"]["new"],
    }, indent=2))


if __name__ == "__main__":
    main()
