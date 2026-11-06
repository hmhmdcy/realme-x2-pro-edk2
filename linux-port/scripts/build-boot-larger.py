#!/usr/bin/env python3
"""Repack the current UEFI carrier with EUD-off BDS and production DTB."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import lzma
import shutil
import struct
import subprocess
import sys
import uuid
import zlib
from pathlib import Path


REPO = Path("/home/cy122/edk2-samurai/repo")
TOOLS = REPO / "Common/edk2/BaseTools/Source/C/bin"
BUILD = REPO / "workspace/Build/samurai/RELEASE_GCC5"
DEFAULT_BOOT = Path(
    "/mnt/e/edk2-samurai-out/standard-arm64-v731/"
    "cmdline-a/boot/boot-eud-production-off.img"
)
DEFAULT_BDS = Path(
    "/mnt/e/edk2-samurai-out/standard-arm64-v731/"
    "final-source-bds5/BdsDxe.efi"
)
DEFAULT_DTB = Path(
    "/mnt/e/edk2-samurai-out/standard-arm64-v731/sm8150-samurai-v731.dtb"
)
DEFAULT_OUT = Path(
    "/mnt/e/edk2-samurai-out/standard-arm64-v731/edk2-source-boot"
)
BDS_GUID = "6d33944a-ec75-4855-a54d-809c75241f6c"
DTB_GUID = "25462cda-221f-47df-ac1d-259cfaa4e326"
PAGE = 2048


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def align(value: int, boundary: int) -> int:
    return (value + boundary - 1) & ~(boundary - 1)


def ffs_size(data: bytes, offset: int) -> int:
    size = int.from_bytes(data[offset + 20:offset + 23], "little")
    if data[offset + 19] & 1:
        size = struct.unpack_from("<Q", data, offset + 24)[0]
    return size


def fv_files(volume: bytes) -> list[dict[str, object]]:
    if volume[40:44] != b"_FVH":
        raise SystemExit("bad firmware-volume header")
    offset = align(struct.unpack_from("<H", volume, 48)[0], 8)
    result = []
    while offset + 24 <= len(volume) and volume[offset:offset + 24] != b"\xff" * 24:
        size = ffs_size(volume, offset)
        if size < 24 or offset + size > len(volume):
            raise SystemExit(f"bad FFS size at {offset:#x}")
        full = volume[offset:offset + size]
        if full[18] != 0xF0:
            header_size = 32 if full[19] & 1 else 24
            header = bytearray(full[:header_size])
            header[17] = header[23] = 0
            if sum(header) % 256:
                raise SystemExit(f"bad FFS header checksum at {offset:#x}")
            result.append({
                "offset": offset,
                "guid": str(uuid.UUID(bytes_le=full[:16])),
                "type": full[18],
                "attributes": full[19],
                "state": full[23],
                "full": full,
            })
        offset = align(offset + size, 8)
    return result


def parse_sections(data: bytes, offset: int = 0) -> list[dict[str, object]]:
    result = []
    while offset + 4 <= len(data) and data[offset:offset + 4] != b"\xff" * 4:
        size = int.from_bytes(data[offset:offset + 3], "little")
        section_type = data[offset + 3]
        header = 4
        if size == 0xFFFFFF:
            size = struct.unpack_from("<I", data, offset + 4)[0]
            header = 8
        if size < header or offset + size > len(data):
            raise SystemExit(f"bad section size at {offset:#x}")
        section = data[offset:offset + size]
        result.append({
            "type": section_type,
            "full": section,
            "body": section[header:],
        })
        offset = align(offset + size, 4)
    return result


def ffs_sections(full: bytes) -> list[dict[str, object]]:
    return parse_sections(full, 32 if full[19] & 1 else 24)


def standalone_ffs(full: bytes) -> bytes:
    data = bytearray(full)
    data[23] ^= 0xFF
    return bytes(data)


def embedded_ffs(full: bytes) -> bytes:
    data = bytearray(full)
    data[23] ^= 0xFF
    return bytes(data)


def parse_boot(boot: bytes) -> dict[str, object]:
    if boot[:8] != b"ANDROID!":
        raise SystemExit("not an Android v1 boot image")
    kernel_size = struct.unpack_from("<I", boot, 8)[0]
    ramdisk_size = struct.unpack_from("<I", boot, 16)[0]
    page, version = struct.unpack_from("<II", boot, 36)
    if page != PAGE or version != 1 or ramdisk_size != 1:
        raise SystemExit("unexpected Android boot geometry")
    payload = boot[page:page + kernel_size]
    decompressor = zlib.decompressobj(31)
    raw = decompressor.decompress(payload) + decompressor.flush()
    if not decompressor.eof or decompressor.unconsumed_tail:
        raise SystemExit("kernel payload is not a complete gzip stream")
    compat = decompressor.unused_data
    if len(raw) != 144 + 7340032:
        raise SystemExit("unexpected kernel raw size")
    shim, compact = raw[:144], raw[144:]
    outer = fv_files(compact)
    containers = [entry for entry in outer if entry["type"] == 0x0B]
    if len(containers) != 1:
        raise SystemExit("compact volume does not contain one container")
    container = containers[0]
    container_sections = ffs_sections(container["full"])
    if len(container_sections) != 1 or container_sections[0]["type"] != 0x02:
        raise SystemExit("unexpected container sections")
    guided = container_sections[0]["full"]
    guided_guid = str(uuid.UUID(bytes_le=guided[4:20]))
    data_offset = struct.unpack_from("<H", guided, 20)[0]
    compressed = guided[data_offset:]
    decoded = lzma.decompress(compressed, format=lzma.FORMAT_ALONE)
    inner_sections = parse_sections(decoded)
    if len(inner_sections) != 1 or inner_sections[0]["type"] != 0x17:
        raise SystemExit("bad FV image section")
    main = inner_sections[0]["body"]
    main_files = fv_files(main)
    if len(main_files) != 101:
        raise SystemExit(f"unexpected main FV file count: {len(main_files)}")
    ramdisk_offset = page + align(kernel_size, page)
    used = ramdisk_offset + PAGE
    return {
        "boot": boot,
        "kernel_size": kernel_size,
        "payload": payload,
        "raw": raw,
        "shim": shim,
        "compact": compact,
        "main": main,
        "compat": compat,
        "ramdisk_page": boot[ramdisk_offset:ramdisk_offset + PAGE],
        "ramdisk_offset": ramdisk_offset,
        "used": used,
        "outer": outer,
        "container": container,
        "guided_guid": guided_guid,
        "main_files": main_files,
    }


def run(argv: list[Path | str], cwd: Path, log: Path) -> None:
    text = [str(value) for value in argv]
    print("+", " ".join(text), flush=True)
    with log.open("wb") as output:
        result = subprocess.run(
            text, cwd=cwd, stdout=output, stderr=subprocess.STDOUT,
            timeout=300,
        )
    if result.returncode:
        raise SystemExit(f"command failed: {text}; see {log}")


def android_id(payload: bytes, ramdisk: bytes) -> bytes:
    digest = hashlib.sha1()
    for value in (payload, ramdisk):
        digest.update(value)
        digest.update(struct.pack("<I", len(value)))
    digest.update(struct.pack("<II", 0, 0))
    return digest.digest() + b"\0" * 12


def build(args: argparse.Namespace) -> int:
    boot = args.boot.read_bytes()
    efi = args.bds.read_bytes()
    dtb = args.dtb.read_bytes()
    parsed = parse_boot(boot)
    output = args.output
    if output.exists():
        raise SystemExit(f"refusing to replace {output}")
    output.mkdir(parents=True)
    files_dir = output / "main-ffs"
    sections_dir = output / "sections"
    files_dir.mkdir()
    sections_dir.mkdir()

    main_files = parsed["main_files"]
    guids = [entry["guid"] for entry in main_files]
    if len(set(guids)) != len(guids) or BDS_GUID not in guids or DTB_GUID not in guids:
        raise SystemExit("unexpected main FV file set")
    bds = next(entry for entry in main_files if entry["guid"] == BDS_GUID)
    dtb_ffs = next(entry for entry in main_files if entry["guid"] == DTB_GUID)
    bds_sections = ffs_sections(bds["full"])
    if [item["type"] for item in bds_sections] != [0x13, 0x10, 0x15]:
        raise SystemExit("unexpected BdsDxe section layout")

    extracted = {}
    for entry in main_files:
        path = files_dir / f"{entry['guid']}.ffs"
        path.write_bytes(standalone_ffs(entry["full"]))
        extracted[entry["guid"]] = path

    (sections_dir / "BDS.depex").write_bytes(bds_sections[0]["full"])
    (sections_dir / "BDS.ui").write_bytes(bds_sections[2]["full"])
    new_bds = files_dir / f"{BDS_GUID}.ffs"
    run([TOOLS / "GenSec", "-s", "EFI_SECTION_PE32",
         "-o", sections_dir / "BDS.pe32", args.bds],
        output, output / "bds-sec.log")
    run([TOOLS / "GenFfs", "-t", "EFI_FV_FILETYPE_DRIVER", "-g", BDS_GUID,
         "-o", new_bds, "-oi", sections_dir / "BDS.depex",
         "-oi", sections_dir / "BDS.pe32", "-oi", sections_dir / "BDS.ui"],
        output, output / "bds-ffs.log")
    extracted[BDS_GUID] = new_bds

    new_dtb = files_dir / f"{DTB_GUID}.ffs"
    run([TOOLS / "GenSec", "-s", "EFI_SECTION_RAW",
         "-o", sections_dir / "DTB.raw", args.dtb],
        output, output / "dtb-sec.log")
    run([TOOLS / "GenFfs", "-t", "EFI_FV_FILETYPE_FREEFORM", "-g", DTB_GUID,
         "-o", new_dtb, "-i", sections_dir / "DTB.raw"],
        output, output / "dtb-ffs.log")
    extracted[DTB_GUID] = new_dtb

    template = (BUILD / "FV/FVMAIN.inf").read_text(encoding="utf-8")
    prefix = template.split("[files]", 1)[0]
    main_config = output / "FVMAIN.inf"
    main_config.write_text(
        prefix + "[files]\n" +
        "\n".join(f"EFI_FILE_NAME = {extracted[guid]}" for guid in guids) +
        "\n",
        encoding="utf-8",
    )
    main_guid = str(uuid.UUID(bytes_le=parsed["main"][16:32]))
    rebuilt_main = output / "main.Fv"
    run([TOOLS / "GenFv", "-g", main_guid, "-i", main_config,
         "-o", rebuilt_main],
        output, output / "main-fv.log")
    rebuilt_main_data = rebuilt_main.read_bytes()
    rebuilt_files = fv_files(rebuilt_main_data)
    if [entry["guid"] for entry in rebuilt_files] != guids:
        raise SystemExit("main FV file order changed")
    changed = []
    for old, new in zip(main_files, rebuilt_files):
        if (old["type"], old["attributes"]) != (new["type"], new["attributes"]):
            raise SystemExit(f"FFS type/attributes changed: {old['guid']}")
        if old["full"] != new["full"]:
            changed.append(old["guid"])
    if not set(changed).issubset({BDS_GUID, DTB_GUID}):
        raise SystemExit(f"unexpected changed FFS set: {changed}")
    new_bds_sections = ffs_sections(
        next(entry for entry in rebuilt_files if entry["guid"] == BDS_GUID)["full"]
    )
    new_dtb_sections = ffs_sections(
        next(entry for entry in rebuilt_files if entry["guid"] == DTB_GUID)["full"]
    )
    if [item["type"] for item in new_bds_sections] != [0x13, 0x10, 0x15]:
        raise SystemExit("new BdsDxe section layout changed")
    if new_bds_sections[1]["body"] != efi:
        raise SystemExit("new BdsDxe PE32 payload is not exact")
    if new_bds_sections[0]["full"] != bds_sections[0]["full"] or \
            new_bds_sections[2]["full"] != bds_sections[2]["full"]:
        raise SystemExit("BdsDxe depex/UI payload changed")
    if len(new_dtb_sections) != 1 or new_dtb_sections[0]["body"] != dtb:
        raise SystemExit("new DTB raw payload is not exact")

    run([TOOLS / "GenSec", "-s", "EFI_SECTION_FIRMWARE_VOLUME_IMAGE",
         "-o", output / "main.fv.sec", rebuilt_main],
        output, output / "fv-image.log")
    run([TOOLS / "GenSec", "--sectionalign", "8",
         "-o", output / "main.aligned", output / "main.fv.sec"],
        output, output / "align.log")
    run([TOOLS / "LzmaCompress", "-e",
         "-o", output / "main.lzma", output / "main.aligned"],
        output, output / "lzma.log")
    run([TOOLS / "GenSec", "-s", "EFI_SECTION_GUID_DEFINED",
         "-g", parsed["guided_guid"], "-r", "PROCESSING_REQUIRED",
         "-o", output / "main.guided", output / "main.lzma"],
        output, output / "guided.log")
    container_guid = parsed["container"]["guid"]
    new_container = output / "container.ffs"
    run([TOOLS / "GenFfs", "-t", "EFI_FV_FILETYPE_FIRMWARE_VOLUME_IMAGE",
         "-g", container_guid, "-o", new_container,
         "-i", output / "main.guided"],
        output, output / "container.log")
    new_container_data = embedded_ffs(new_container.read_bytes())

    compact = bytearray(parsed["compact"])
    container_offset = parsed["container"]["offset"]
    free = parsed["compact"][
        container_offset + len(parsed["container"]["full"]):
    ]
    if any(value != 0xFF for value in free):
        raise SystemExit("compact FV has non-free data after the container")
    capacity = len(compact) - container_offset
    if len(new_container_data) > capacity:
        raise SystemExit("new container does not fit in the compact FV")
    compact[container_offset:] = b"\xff" * capacity
    compact[container_offset:container_offset + len(new_container_data)] = new_container_data
    parsed_compact = fv_files(bytes(compact))
    sec_old = next(entry for entry in parsed["outer"]
                   if entry["guid"] != container_guid)
    sec_new = next(entry for entry in parsed_compact
                   if entry["guid"] == sec_old["guid"])
    if sec_new["offset"] != sec_old["offset"] or sec_new["full"] != sec_old["full"]:
        raise SystemExit("SEC FFS changed while replacing the container")
    container_new = next(entry for entry in parsed_compact
                         if entry["guid"] == container_guid)
    if container_new["offset"] != container_offset or \
            container_new["full"] != new_container_data:
        raise SystemExit("container was not installed exactly")

    raw = parsed["shim"] + bytes(compact)
    payload = gzip.compress(raw, compresslevel=9, mtime=0) + parsed["compat"]
    kernel_size = len(payload)
    ramdisk_offset = PAGE + align(kernel_size, PAGE)
    used = ramdisk_offset + PAGE
    if used > len(boot):
        raise SystemExit(
            f"new kernel needs {used} bytes, past partition size {len(boot)}"
        )
    header = bytearray(boot[:PAGE])
    header[8:12] = struct.pack("<I", kernel_size)
    header[576:608] = android_id(payload, b"\n")
    candidate = (
        bytes(header) + payload +
        b"\0" * (ramdisk_offset - PAGE - kernel_size) +
        parsed["ramdisk_page"] + b"\0" * (len(boot) - used)
    )
    if len(candidate) != len(boot):
        raise SystemExit("boot carrier length changed")
    check = parse_boot(candidate)
    if check["raw"] != raw or check["main"] != rebuilt_main_data:
        raise SystemExit("rebuilt candidate does not decode to the new main FV")
    if check["compat"] != parsed["compat"] or \
            check["shim"] != parsed["shim"]:
        raise SystemExit("shim or compatibility DTB changed")
    if candidate[576:608] != android_id(payload, b"\n"):
        raise SystemExit("Android v1 ID mismatch")
    old_header = bytearray(boot[:PAGE])
    new_header = bytearray(candidate[:PAGE])
    for value in (old_header, new_header):
        value[8:12] = b"\0" * 4
        value[576:608] = b"\0" * 32
    if old_header != new_header:
        raise SystemExit("Android header changed outside size and ID")

    target = output / "boot-eud-production-off.img"
    target.write_bytes(candidate)
    result = {
        "passed": True,
        "source_boot": str(args.boot),
        "source_boot_sha256": sha(boot),
        "bds_efi": str(args.bds),
        "bds_efi_sha256": sha(efi),
        "dtb": str(args.dtb),
        "dtb_sha256": sha(dtb),
        "boot": str(target),
        "boot_sha256": sha(candidate),
        "kernel_size": kernel_size,
        "new_used": used,
        "old_used": parsed["used"],
        "changed_main_ffs": changed,
        "unchanged_main_ffs": len(guids) - len(changed),
        "main_fv_sha256": sha(rebuilt_main_data),
        "container_sha256": sha(new_container_data),
        "container_offset": container_offset,
        "SEC_preserved": True,
        "compat_preserved": True,
        "ramdisk_preserved": True,
        "header_only_size_id_changed": True,
    }
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n",
                                        encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--boot", type=Path, default=DEFAULT_BOOT)
    parser.add_argument("--bds", type=Path, default=DEFAULT_BDS)
    parser.add_argument("--dtb", type=Path, default=DEFAULT_DTB)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not args.execute:
        parsed = parse_boot(args.boot.read_bytes())
        print(json.dumps({
            "boot": str(args.boot),
            "boot_sha256": sha(parsed["boot"]),
            "main_ffs": len(parsed["main_files"]),
            "kernel_size": parsed["kernel_size"],
            "used": parsed["used"],
            "output": str(args.output),
        }, indent=2))
        return 0
    return build(args)


if __name__ == "__main__":
    sys.exit(main())
