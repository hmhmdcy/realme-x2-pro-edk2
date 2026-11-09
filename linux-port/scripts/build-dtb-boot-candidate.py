#!/usr/bin/env python3
"""Build a boot image that changes only the embedded OS-facing DTB."""
from pathlib import Path
import argparse
import hashlib
import json
import lzma
import os
import shutil
import struct
import subprocess
import uuid
import zlib

REPO_ROOT = Path(__file__).resolve().parents[2]


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def load_helpers():
    source = (
        REPO_ROOT / "reference/kernel104/verify-firmware.py"
    ).read_text(encoding="utf-8").split("dt_audit=")[0]
    namespace = {}
    exec(compile(source, "verify-firmware-helpers", "exec"), namespace)
    return namespace


def unpack_boot(boot, compat, helpers):
    align = helpers["align"]
    fv = helpers["fv"]
    sections = helpers["sections"]
    lz_guid = helpers["lz_guid"]

    assert boot[:8] == b"ANDROID!"
    kernel_size, ramdisk_size, second_size, page, version = [
        struct.unpack_from("<I", boot, offset)[0]
        for offset in (8, 16, 24, 36, 40)
    ]
    assert page == 2048 and version == 1
    assert ramdisk_size == 1 and second_size == 0
    size = (
        page
        + align(kernel_size, page)
        + align(ramdisk_size, page)
        + align(second_size, page)
    )
    decompressor = zlib.decompressobj(31)
    payload = boot[page:page + kernel_size]
    raw = decompressor.decompress(payload) + decompressor.flush()
    assert decompressor.eof and not decompressor.unconsumed_tail
    assert decompressor.unused_data == compat
    shim = raw[:144]
    fd = raw[144:]
    assert len(fd) == 0x700000

    compact = fv(fd)
    images = [item for item in compact.values() if item["type"] == 0xB]
    assert len(images) == 1 and len(images[0]["sections"]) == 1
    section_type, body, section = images[0]["sections"][0]
    assert section_type == 2
    assert str(uuid.UUID(bytes_le=body[:16])) == lz_guid
    offset, _attrs = struct.unpack_from("<HH", body, 16)
    nested = sections(
        lzma.decompress(section[offset:], format=lzma.FORMAT_ALONE)
    )
    assert len(nested) == 1 and nested[0][0] == 0x17
    main = nested[0][1]

    return {
        "boot": boot[:size],
        "size": size,
        "page": page,
        "shim": shim,
        "fd": fd,
        "main": main,
        "modules": fv(main),
        "ramdisk": boot[
            page + align(kernel_size, page):
            page + align(kernel_size, page) + ramdisk_size
        ],
    }


def normalized_header(boot):
    header = bytearray(boot[:2048])
    header[8:12] = b"\0" * 4
    header[576:608] = b"\0" * 32
    return bytes(header)


parser = argparse.ArgumentParser()
parser.add_argument("--repo", required=True, type=Path)
parser.add_argument("--source-boot", required=True, type=Path)
parser.add_argument("--candidate-dtb", required=True, type=Path)
parser.add_argument("--output-dir", required=True, type=Path)
parser.add_argument("--toolchain", default="GCC5")
parser.add_argument("--partition-size", default=100663296, type=int)
args = parser.parse_args()

source_boot = args.source_boot.read_bytes()
dtb = args.candidate_dtb.read_bytes()
assert len(source_boot) == args.partition_size
assert dtb[:4] == bytes.fromhex("d00dfeed")
args.output_dir.mkdir(parents=True, exist_ok=True)

repo = args.repo
blob = (
    repo
    / "Platform/Realme/sm8150/FdtBlob/samurai/"
      "sm8150-realme-samurai.dtb"
)
compat = (
    repo / "Platform/Realme/sm8150/FdtBlob_compat/samurai.dtb"
).read_bytes()
fvdir = repo / "workspace/Build/samurai/RELEASE_GCC5/FV"
outputs = {
    "boot": repo / "boot-samurai.img",
    "fd": fvdir / "SM8150_UEFI.fd",
    "fvmain": fvdir / "FVMAIN.Fv",
    "fvmain_compact": fvdir / "FVMAIN_COMPACT.Fv",
}
old_blob = blob.read_bytes()
saved = {
    name: path.read_bytes()
    for name, path in outputs.items()
    if path.is_file()
}

env = os.environ.copy()
local_uuid = repo.parent / "local/uuid"
if (local_uuid / "usr/include").is_dir():
    env["CPATH"] = str(local_uuid / "usr/include")
if (local_uuid / "usr/lib/x86_64-linux-gnu").is_dir():
    env["LIBRARY_PATH"] = str(local_uuid / "usr/lib/x86_64-linux-gnu")

try:
    blob.write_bytes(dtb)
    with (args.output_dir / "firmware-build.log").open("wb") as log:
        subprocess.run(
            [
                "./build.sh",
                "-d",
                "samurai",
                "--toolchain",
                args.toolchain,
                "--skip-rootfs-gen",
            ],
            cwd=repo,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=True,
        )
    built = {name: path.read_bytes() for name, path in outputs.items()}
finally:
    blob.write_bytes(old_blob)
    for name, path in outputs.items():
        if name in saved:
            path.write_bytes(saved[name])
        elif path.exists():
            path.unlink()

assert blob.read_bytes() == old_blob
assert all(
    path.read_bytes() == saved[name]
    for name, path in outputs.items()
    if name in saved
)
assert all(
    not path.exists()
    for name, path in outputs.items()
    if name not in saved
)

built_dir = args.output_dir / "built"
built_dir.mkdir(parents=True, exist_ok=True)
for name, data in built.items():
    (built_dir / name).write_bytes(data)

helpers = load_helpers()
old = unpack_boot(source_boot, compat, helpers)
new = unpack_boot(built["boot"], compat, helpers)
dt_guid = helpers["dt_guid"]

assert old["shim"] == new["shim"]
assert old["ramdisk"] == new["ramdisk"]
assert normalized_header(old["boot"]) == normalized_header(new["boot"])
assert old["modules"].keys() == new["modules"].keys()

changed = []
non_dtb_changes = []
for guid, module in old["modules"].items():
    replacement = new["modules"][guid]
    assert (module["type"], module["attrs"]) == (
        replacement["type"], replacement["attrs"])
    if module["body"] != replacement["body"]:
        if guid == dt_guid:
            changed.append({
                "guid": guid,
                "name": replacement["name"],
                "classification": "embedded-os-dtb",
            })
        elif replacement["name"] in ("PlatformSmbiosDxe", "BdsDxe", "UiApp"):
            non_dtb_changes.append({
                "guid": guid,
                "name": replacement["name"],
                "classification": "non_dtb_module_change_requires_review",
            })
        else:
            raise AssertionError((guid, replacement["name"]))
assert len(changed) == 1 and changed[0]["guid"] == dt_guid
dt_sections = new["modules"][dt_guid]["sections"]
assert len(dt_sections) == 1 and dt_sections[0][0] == 0x19
assert dt_sections[0][1] == dtb
assert built["fd"] == new["fd"]
assert built["fvmain"] == new["main"]

candidate = new["boot"] + source_boot[new["size"]:]
assert len(candidate) == args.partition_size
assert candidate[new["size"]:] == source_boot[new["size"]:]
candidate_path = args.output_dir / "boot-dtb-vendor-split.img"
candidate_path.write_bytes(candidate)

report = {
    "schema": "samurai-dtb-only-boot-candidate-v1",
    "source_boot": str(args.source_boot),
    "source_boot_sha256": sha256(source_boot),
    "candidate_dtb": str(args.candidate_dtb),
    "candidate_dtb_sha256": sha256(dtb),
    "boot_candidate": str(candidate_path),
    "boot_candidate_sha256": sha256(candidate),
    "partition_bytes": len(candidate),
    "changed_modules": changed,
    "non_dtb_module_changes": non_dtb_changes,
    "offline_gate_passed": not non_dtb_changes,
    "classification": (
        "requires_minimal_repack" if non_dtb_changes else "dtb_only"
    ),
    "bootshim_unchanged": old["shim"] == new["shim"],
    "ramdisk_unchanged": old["ramdisk"] == new["ramdisk"],
    "android_header_unchanged_except_size_and_hash": (
        normalized_header(old["boot"]) == normalized_header(new["boot"])
    ),
    "embedded_dtb_matches_candidate": True,
    "other_fv_modules_unchanged": not non_dtb_changes,
    "repository_fdtblob_restored": True,
    "repository_build_outputs_restored": True,
}
(args.output_dir / "result.json").write_text(
    json.dumps(report, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(json.dumps(report, indent=2, sort_keys=True))
