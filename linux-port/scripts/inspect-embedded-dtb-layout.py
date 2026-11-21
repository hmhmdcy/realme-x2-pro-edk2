#!/usr/bin/env python3
"""Print the FFS layout around the embedded OS DTB in a samurai boot image."""

from __future__ import annotations

import argparse
import json
import lzma
import struct
import uuid
import zlib
from pathlib import Path

DT_GUID = "25462cda-221f-47df-ac1d-259cfaa4e326"
LZ_GUID = ""


def align(value: int, alignment: int) -> int:
    return (value + alignment - 1) // alignment * alignment


def sections(buffer: bytes) -> list[dict]:
    rows = []
    offset = 0
    while offset < len(buffer):
        if all(byte in (0, 255) for byte in buffer[offset:]):
            break
        size = int.from_bytes(buffer[offset:offset + 3], "little")
        section_type = buffer[offset + 3]
        header_size = 4
        if size == 0xFFFFFF:
            size, header_size = struct.unpack_from(
                "<I", buffer, offset + 4
            )[0], 8
        rows.append({
            "offset": offset,
            "size": size,
            "type": section_type,
            "header_size": header_size,
            "body": buffer[offset + header_size:offset + size],
        })
        offset = align(offset + size, 4)
    return rows


def ffs_files(buffer: bytes) -> list[dict]:
    assert buffer[40:44] == b"_FVH"
    length = struct.unpack_from("<Q", buffer, 32)[0]
    header_size = struct.unpack_from("<H", buffer, 48)[0]
    assert length == len(buffer)
    rows = []
    offset = align(header_size, 8)
    while offset + 24 <= len(buffer):
        if buffer[offset:offset + 24] == b"\xff" * 24:
            break
        attributes = buffer[offset + 19]
        size = int.from_bytes(buffer[offset + 20:offset + 23], "little")
        file_header_size = 24
        if attributes & 1:
            size, file_header_size = struct.unpack_from(
                "<Q", buffer, offset + 24
            )[0], 32
        guid = str(uuid.UUID(bytes_le=buffer[offset:offset + 16]))
        body = buffer[offset + file_header_size:offset + size]
        rows.append({
            "guid": guid,
            "offset": offset,
            "size": size,
            "type": buffer[offset + 18],
            "attributes": attributes,
            "header_size": file_header_size,
            "sections": sections(body),
        })
        offset = align(offset + size, 8)
    return rows


def raw_fd(boot: bytes) -> bytes:
    assert boot[:8] == b"ANDROID!"
    kernel_size, ramdisk_size, second_size, page, version = [
        struct.unpack_from("<I", boot, offset)[0]
        for offset in (8, 16, 24, 36, 40)
    ]
    assert page == 2048 and version == 1
    assert ramdisk_size == 1 and second_size == 0
    decompressor = zlib.decompressobj(31)
    raw = (
        decompressor.decompress(boot[page:page + kernel_size])
        + decompressor.flush()
    )
    assert decompressor.eof and not decompressor.unconsumed_tail
    return raw[144:]


def compressed_fv(fd: bytes) -> dict:
    images = [
        row for row in ffs_files(fd)
        if row["type"] == 0xB and len(row["sections"]) == 1
    ]
    assert len(images) == 1
    guided = images[0]["sections"][0]
    assert guided["type"] == 2
    return guided


def embedded_main_fv(boot: bytes) -> tuple[str, bytes]:
    guided = compressed_fv(raw_fd(boot))
    lz_guid = str(uuid.UUID(bytes_le=guided["body"][:16]))
    compressed_offset = struct.unpack_from("<H", guided["body"], 16)[0]
    compressed_offset -= guided["header_size"]
    plain = lzma.decompress(
        guided["body"][compressed_offset:], format=lzma.FORMAT_ALONE
    )
    nested = sections(plain)
    assert len(nested) == 1 and nested[0]["type"] == 0x17
    return lz_guid, nested[0]["body"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("boot", type=Path)
    parser.add_argument("--json", type=Path)
    parser.add_argument("--dtb-out", type=Path)
    args = parser.parse_args()

    boot = args.boot.read_bytes()
    lz_guid, main_fv = embedded_main_fv(boot)
    modules = ffs_files(main_fv)

    print(f"lz_guid={lz_guid}")
    print(f"main_fv_bytes={len(main_fv)}")
    print(f"main_fv_modules={len(modules)}")
    previous_end = 0
    for row in modules:
        gap = row["offset"] - previous_end
        marker = " <- DTB" if row["guid"] == DT_GUID else ""
        print(
            f"offset={row['offset']:08x} size={row['size']:6d} "
            f"gap={gap:5d} type=0x{row['type']:02x} {row['guid']}{marker}"
        )
        for section in row["sections"]:
            print(
                f"    section type=0x{section['type']:02x} "
                f"offset={section['offset']:6d} size={section['size']:6d} "
                f"body={len(section['body'])}"
            )
        previous_end = row["offset"] + row["size"]
    print(f"last_end={previous_end}")
    print(f"tail_bytes={len(main_fv) - previous_end}")

    if args.dtb_out:
        for row in modules:
            if row["guid"] != DT_GUID:
                continue
            assert len(row["sections"]) == 1
            args.dtb_out.write_bytes(row["sections"][0]["body"])
            print(f"wrote_dtb={args.dtb_out}")
            break

    if args.json:
        args.json.write_text(
            json.dumps(
                {
                    "boot": str(args.boot),
                    "lz_guid": lz_guid,
                    "main_fv_bytes": len(main_fv),
                    "last_end": previous_end,
                    "tail_bytes": len(main_fv) - previous_end,
                    "modules": [
                        {
                            "guid": row["guid"],
                            "type": row["type"],
                            "offset": row["offset"],
                            "size": row["size"],
                            "header_size": row["header_size"],
                            "sections": [
                                {
                                    "type": section["type"],
                                    "offset": section["offset"],
                                    "size": section["size"],
                                    "body_bytes": len(section["body"]),
                                }
                                for section in row["sections"]
                            ],
                        }
                        for row in modules
                    ],
                },
                indent=2,
                sort_keys=True,
            ) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
