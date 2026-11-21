from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(r"E:\RealmeX2Pro edk2\reference\charging-management-20261023\integration-20261026")
TRIAL = ROOT / "trial-517-r9-status-precharge"
OUT = Path(r"E:\edk2-samurai-out\charging-management-20261023")
FAT = OUT / "charging-integration-20261027-fat-private-07"
BOOT = OUT / "charging-integration-20261027-boot-private-09"
BUILD = Path(r"\\wsl.localhost\Ubuntu\home\cy122\charging-management-20261023\charging-integration-20261026-01\build")
KERNEL_VERSION = "#524 SMP PREEMPT Tue Oct 27 07:06:49 CST 2026"
BUILD_PINS = {
    "Image": ("8340243e4078761a05a5de65cb132e59bd6f43854e3dc4cc4951173c078f0f6c", 59374080),
    "vmlinux": ("d6241c760e0135ca7ccbd3ef2cdd1b9ae095ec59e596e137b3b09ebe87844ea8", 191012208),
    "System.map": ("a4b1cca0e407037ab56c7bc78ba88042848d54d4ab32977ff107d5b14eafc207", 9023805),
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
    boot_image = BOOT / "boot-eud-off-route-private-r13.img"
    fat_receipt = FAT / "result.json"
    fat_image = FAT / "logdump-mp2650-r10-private.img"

    manifest["boot_receipt"].update(
        path=str(boot_receipt),
        bytes=boot_receipt.stat().st_size,
        sha256=sha(boot_receipt),
        boot_path_suffix="charging-management-20261023/charging-integration-20261027-boot-private-09/boot-eud-off-route-private-r13.img",
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
        fat_receipt_path=str(fat_receipt),
        fat_receipt_sha256=sha(fat_receipt),
    )
    module_path = TRIAL / manifest["kernel_module"]["source"]
    manifest["kernel_module"]["new_sha256"] = sha(module_path)
    manifest["kernel_module"]["new_bytes"] = module_path.stat().st_size
    manifest["kernel_version"] = KERNEL_VERSION
    manifest["postboot"]["version"] = KERNEL_VERSION
    manifest["runtime_dtb"]["fat_receipt_path"] = str(fat_receipt)
    manifest["runtime_dtb"]["fat_receipt_sha256"] = sha(fat_receipt)

    provenance = manifest["image_provenance"]
    provenance["kernel_build_label"] = "#524"
    provenance["kernel_version"] = KERNEL_VERSION
    provenance["kernel_version_suffix"] = "SMP PREEMPT Tue Oct 27 07:06:49 CST 2026"
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
