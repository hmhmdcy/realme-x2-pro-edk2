#!/usr/bin/env python3
"""Replace the embedded OS DTB in a boot image without rebuilding firmware."""
from pathlib import Path
import argparse
import gzip
import hashlib
import json
import lzma
import struct
import sys
import uuid
import zlib

REPO_ROOT = Path(__file__).resolve().parents[2]
DT_GUID = "25462cda-221f-47df-ac1d-259cfaa4e326"


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def align(value, boundary):
    return (value + boundary - 1) // boundary * boundary


def sections(buffer):
    result = []
    offset = 0
    while offset < len(buffer):
        if all(byte in (0, 255) for byte in buffer[offset:]):
            break
        size = int.from_bytes(buffer[offset:offset + 3], "little")
        section_type = buffer[offset + 3]
        header_size = 4
        if size == 0xFFFFFF:
            size, header_size = struct.unpack_from(
                "<I", buffer, offset + 4)[0], 8
        result.append({
            "offset": offset,
            "size": size,
            "type": section_type,
            "header_size": header_size,
            "body": buffer[offset + header_size:offset + size],
            "raw": buffer[offset:offset + size],
        })
        offset = align(offset + size, 4)
    return result


def firmware_volume(buffer):
    assert buffer[40:44] == b"_FVH"
    length = struct.unpack_from("<Q", buffer, 32)[0]
    header_size = struct.unpack_from("<H", buffer, 48)[0]
    assert length == len(buffer)
    result = {}
    offset = align(header_size, 8)
    while offset + 24 <= len(buffer):
        if buffer[offset:offset + 24] == b"\xff" * 24:
            break
        header = bytearray(buffer[offset:offset + 24])
        file_type, attributes = header[18], header[19]
        size = int.from_bytes(header[20:23], "little")
        file_header_size = 24
        if attributes & 1:
            size, file_header_size = struct.unpack_from(
                "<Q", buffer, offset + 24)[0], 32
            header = bytearray(buffer[offset:offset + file_header_size])
        guid = str(uuid.UUID(bytes_le=bytes(buffer[offset:offset + 16])))
        body = buffer[offset + file_header_size:offset + size]
        result[guid] = {
            "offset": offset,
            "size": size,
            "header_size": file_header_size,
            "type": file_type,
            "attributes": attributes,
            "body": body,
            "sections": sections(body),
        }
        offset = align(offset + size, 8)
    return result


def parse_boot(boot):
    assert boot[:8] == b"ANDROID!"
    fields = [
        struct.unpack_from("<I", boot, offset)[0]
        for offset in (8, 16, 24, 36, 40)
    ]
    kernel_size, ramdisk_size, second_size, page, version = fields
    assert page == 2048 and version == 1
    assert ramdisk_size == 1 and second_size == 0
    used_size = page + align(kernel_size, page) + align(ramdisk_size, page)
    decompressor = zlib.decompressobj(31)
    payload = boot[page:page + kernel_size]
    raw = decompressor.decompress(payload) + decompressor.flush()
    assert decompressor.eof and not decompressor.unconsumed_tail
    compat = decompressor.unused_data
    assert raw[144:]
    return {
        "header": boot[:page],
        "payload": payload,
        "raw": raw,
        "shim": raw[:144],
        "fd": raw[144:],
        "compat": compat,
        "ramdisk": boot[
            page + align(kernel_size, page):
            page + align(kernel_size, page) + ramdisk_size
        ],
        "kernel_size": kernel_size,
        "ramdisk_size": ramdisk_size,
        "page": page,
        "used_size": used_size,
    }


def compact_fv(fd):
    compact = firmware_volume(fd)
    matches = [
        item for item in compact.values()
        if item["type"] == 0xB and len(item["sections"]) == 1
    ]
    assert len(matches) == 1
    module = matches[0]
    section = module["body"]
    guided = sections(module["body"])[0]
    assert guided["type"] == 2
    offset, attributes = struct.unpack_from("<HH", guided["raw"], 20)
    assert attributes == 1 and offset >= 24
    compressed = guided["raw"][offset:]
    plain = lzma.decompress(compressed, format=lzma.FORMAT_ALONE)
    plain_sections = sections(plain)
    assert len(plain_sections) == 1 and plain_sections[0]["type"] == 0x17
    return {
        "compact": compact,
        "module": module,
        "guided": guided,
        "compressed": compressed,
        "plain": plain,
        "main": plain_sections[0]["body"],
    }


parser = argparse.ArgumentParser()
parser.add_argument("--source-boot", required=True, type=Path)
parser.add_argument("--candidate-dtb", required=True, type=Path)
parser.add_argument("--compressed-main", type=Path)
parser.add_argument(
    "--dump-modified-plain",
    type=Path,
    help="write the uncompressed modified main FV and exit before compression",
)
parser.add_argument("--output-dir", required=True, type=Path)
parser.add_argument("--partition-size", default=100663296, type=int)
args = parser.parse_args()

source = args.source_boot.read_bytes()
dtb = args.candidate_dtb.read_bytes()
assert len(source) == args.partition_size
assert dtb[:4] == bytes.fromhex("d00dfeed")
args.output_dir.mkdir(parents=True, exist_ok=True)

old = parse_boot(source)
compact = compact_fv(old["fd"])
main = bytearray(compact["main"])
main_fv = firmware_volume(main)
dt_file = main_fv[DT_GUID]
dt_sections = sections(dt_file["body"])
assert len(dt_sections) == 1 and dt_sections[0]["type"] == 0x19
dt_section = dt_sections[0]
old_dtb_bytes = dt_section["body"]
assert old_dtb_bytes[:4] == bytes.fromhex("d00dfeed")
assert len(dtb) <= len(old_dtb_bytes)

new_dtb_padded = dtb + b"\0" * (len(old_dtb_bytes) - len(dtb))
start = dt_file["offset"] + dt_file["header_size"] + dt_section["offset"] \
    + dt_section["header_size"]
main[start:start + len(new_dtb_padded)] = new_dtb_padded

plain = bytearray(compact["plain"])
plain_sections = sections(plain)
assert len(plain_sections) == 1 and plain_sections[0]["type"] == 0x17
plain_section = plain_sections[0]
assert plain_section["body"] == compact["main"]
main_start = plain_section["offset"] + plain_section["header_size"]
plain[main_start:main_start + len(main)] = main

if args.dump_modified_plain:
    args.dump_modified_plain.parent.mkdir(parents=True, exist_ok=True)
    args.dump_modified_plain.write_bytes(plain)
    print(
        json.dumps({
            "modified_plain": str(args.dump_modified_plain),
            "modified_plain_sha256": sha256(plain),
            "modified_plain_bytes": len(plain),
        }, indent=2, sort_keys=True)
    )
    sys.exit(0)

if not args.compressed_main:
    parser.error(
        "--compressed-main is required unless --dump-modified-plain is used"
    )

compressed = args.compressed_main.read_bytes()
assert compressed[:5] == compact["compressed"][:5]
assert int.from_bytes(compressed[5:13], "little") == len(plain)
assert lzma.decompress(
    compressed, format=lzma.FORMAT_ALONE
) == bytes(plain)
new_guided_size = 24 + len(compressed)
assert new_guided_size <= compact["guided"]["size"]

new_fd = bytearray(old["fd"])
module_offset = compact["module"]["offset"]
section_offset = module_offset + compact["module"]["header_size"]
section = bytearray(old["fd"][section_offset:section_offset + compact[
    "guided"]["size"]])
section[0:3] = new_guided_size.to_bytes(3, "little")
section[24:] = compressed
if len(section) < compact["guided"]["size"]:
    section += b"\xff" * (compact["guided"]["size"] - len(section))
new_fd[section_offset:section_offset + len(section)] = section

new_payload = gzip.compress(
    old["shim"] + bytes(new_fd), compresslevel=9, mtime=0
) + old["compat"]
new_header = bytearray(old["header"])
new_header[8:12] = struct.pack("<I", len(new_payload))

identity = hashlib.sha1()
identity.update(new_payload)
identity.update(struct.pack("<I", len(new_payload)))
identity.update(old["ramdisk"])
identity.update(struct.pack("<I", len(old["ramdisk"])))
identity.update(b"")
identity.update(struct.pack("<I", 0))
identity.update(b"")
identity.update(struct.pack("<I", 0))
new_header[576:608] = identity.digest() + b"\0" * 12

new_used = (
    old["page"]
    + align(len(new_payload), old["page"])
    + align(len(old["ramdisk"]), old["page"])
)
assert new_used <= args.partition_size
candidate = (
    bytes(new_header)
    + new_payload
    + b"\0" * (align(len(new_payload), old["page"]) - len(new_payload))
    + old["ramdisk"]
    + b"\0" * (align(len(old["ramdisk"]), old["page"]) - len(old["ramdisk"]))
    + b"\0" * (args.partition_size - new_used)
)

print(
    "layout",
    {"header": len(new_header), "payload": len(new_payload),
     "ramdisk": len(old["ramdisk"]), "used": new_used,
     "candidate": len(candidate)},
    flush=True,
)
candidate_path = args.output_dir / "boot-dtb-vendor-split-inplace.img"
candidate_path.write_bytes(candidate)
parsed_new = parse_boot(candidate)
new_compact = compact_fv(parsed_new["fd"])
new_main = firmware_volume(new_compact["main"])
new_dt_file = new_main[DT_GUID]
new_dt = sections(new_dt_file["body"])[0]["body"]
assert new_dt[:len(dtb)] == dtb
assert new_dt[len(dtb):] == b"\0" * (len(new_dt) - len(dtb))

changed = [
    guid for guid in main_fv
    if main_fv[guid]["body"] != new_main[guid]["body"]
]
assert changed == [DT_GUID], changed
assert new_compact["main"] == compact["main"].replace(
    old_dtb_bytes, new_dtb_padded, 1
)

report = {
    "schema": "samurai-dtb-boot-inplace-v1",
    "source_boot": str(args.source_boot),
    "source_boot_sha256": sha256(source),
    "candidate_dtb": str(args.candidate_dtb),
    "candidate_dtb_sha256": sha256(dtb),
    "old_embedded_dtb_sha256": sha256(old_dtb_bytes),
    "old_embedded_dtb_bytes": len(old_dtb_bytes),
    "new_embedded_dtb_bytes": len(dtb),
    "new_embedded_dtb_padded_sha256": sha256(new_dtb_padded),
    "embedded_dtb_padding_bytes": len(new_dtb_padded) - len(dtb),
    "compressed_main": str(args.compressed_main),
    "compressed_main_sha256": sha256(compressed),
    "compressed_main_header_hex": compressed[:13].hex(),
    "compressed_main_uncompressed_bytes": len(plain),
    "compressed_main_known_size_verified": True,
    "boot_candidate": str(candidate_path),
    "boot_candidate_sha256": sha256(candidate),
    "partition_bytes": len(candidate),
    "bootshim_unchanged": old["shim"] == parsed_new["shim"],
    "compat_tail_unchanged": old["compat"] == parsed_new["compat"],
    "ramdisk_unchanged": old["ramdisk"] == parsed_new["ramdisk"],
    "android_header_changed_fields": ["kernel_size", "id"],
    "source_kernel_size": old["kernel_size"],
    "candidate_kernel_size": len(new_payload),
    "embedded_dtb_matches_candidate": True,
    "compressed_main_decodes_to_modified_plain": True,
    "changed_ffs_guids": changed,
    "non_dtb_ffs_body_changes": 0,
    "other_fv_modules_unchanged": True,
    "inner_fv_checksums_unchanged": True,
}
(args.output_dir / "result.json").write_text(
    json.dumps(report, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(json.dumps(report, indent=2, sort_keys=True))
