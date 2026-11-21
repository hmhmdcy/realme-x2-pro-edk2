#!/usr/bin/env python3
"""Build the r7 boot receipt from boot-private-05 and the r6 EUD-off DTB."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import lzma
import os
import shutil
import struct
import subprocess
import sys
import traceback
from pathlib import Path

sys.dont_write_bytecode = True
if sys.flags.optimize:
    raise RuntimeError("non-optimized interpreter required")

OUT = Path(
    "/mnt/e/edk2-samurai-out/charging-management-20261023/"
    "charging-integration-20261027-boot-private-01"
)
BASE = Path(
    "/mnt/e/edk2-samurai-out/charging-management-20261023/"
    "charging-integration-20261026-boot-private-05"
)
BASE_BOOT = BASE / "boot-tcpm-usb-budget508-private.img"
BASE_RECEIPT = BASE / "result.json"
BASE_FVMAIN = BASE / "FVMAIN.inf"
BASE_COMPACT = BASE / "FVMAIN_COMPACT.inf"
BASE_SEC_INPUTS = BASE / "inputs"

RUNTIME_DTB = Path(
    "/mnt/e/edk2-samurai-out/charging-management-20261023/"
    "charging-integration-20261026-dtb-private-02/"
    "samurai-eud-off-route-okay.dtb"
)
RUNTIME_FAT_RECEIPT = Path(
    "/mnt/e/edk2-samurai-out/charging-management-20261023/"
    "charging-integration-20261027-fat-private-01/result.json"
)
PACKAGER = Path(
    "/mnt/e/RealmeX2Pro edk2/reference/charging-oem-audit-20261023/"
    "tcpm-usb-budget-candidate/package-boot.py"
)

BASE_BOOT_SHA256 = "8af84ca536c9d4e1f09d7395adb303ba6f2ed6fa9138adef074df95e68e56680"
BASE_BOOT_BYTES = 100_663_296
BASE_RECEIPT_SHA256 = "139024d09a778233fe6712f496095f17725f7b1979f8f4292c2848f16fdace97"
BASE_DTB_SHA256 = "9aa3e6fce7833f294a2dd7dc9b8f9d4fc95f3627d0c2386ba2ce183bc4316cd6"
BASE_DTB_BYTES = 116_966
NEW_DTB_SHA256 = "d7d8a7da7a3fc68b37faceda0fd7c7f506fbbd17b7a510c15cb978b9160acf1b"
NEW_DTB_BYTES = 116_962
BDS_EFI_SHA256 = "8cf009ba218a3c9e08e81c47dbed3a4047f2e43b9a16b9aa75980dcc3735dc09"
FAT_IMAGE_SHA256 = "6e45cbb780b7de690f714a17b54524369b630eccff8ee773acbbb38a59f90f2f"
FAT_RECEIPT_SHA256 = "d0dad3c362529d2a5c00e37b4ba4349cb591318b0dd3789eb100a7e15a19e420"
PACKAGE_LIMIT = 6_686_720
GZIP_MTIME_NS = 1_792_719_172_000_000_000


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def save_json(path: Path, value: dict) -> None:
    with path.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def load_packager():
    spec = importlib.util.spec_from_file_location("boot05_packager", PACKAGER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_tool(
    result: dict,
    name: str,
    executable: str,
    arguments: list[object],
    stage: str,
    stdin_path: Path | None = None,
    stdout_path: Path | None = None,
) -> None:
    argv = [executable] + [str(value) for value in arguments]
    entry = {"stage": stage, "argv": argv}
    result["commands"].append(entry)
    save_json(OUT / "result.json", result)
    stdout_target = stdout_path or (OUT / f"{stage}.stdout")
    stderr_target = OUT / f"{stage}.stderr"
    with stderr_target.open("xb") as stderr:
        if stdin_path is None:
            with stdout_target.open("xb") as stdout:
                process = subprocess.run(
                    argv,
                    cwd=OUT,
                    stdin=subprocess.DEVNULL,
                    stdout=stdout,
                    stderr=stderr,
                    env={**os.environ, "PATH": "/usr/bin:/bin", "GZIP": ""},
                    check=False,
                )
        else:
            with stdin_path.open("rb") as source, stdout_target.open("xb") as stdout:
                process = subprocess.run(
                    argv,
                    cwd=OUT,
                    stdin=source,
                    stdout=stdout,
                    stderr=stderr,
                    env={**os.environ, "PATH": "/usr/bin:/bin", "GZIP": ""},
                    check=False,
                )
    entry.update(
        returncode=process.returncode,
        stdout=str(stdout_target),
        stderr=str(stderr_target),
        stdout_sha256=file_sha256(stdout_target),
        stderr_sha256=file_sha256(stderr_target),
    )
    save_json(OUT / "result.json", result)
    assert process.returncode == 0, f"{stage} failed: {process.returncode}"


def equal_tail(left: Path, right: Path, offset: int) -> bool:
    with left.open("rb") as a, right.open("rb") as b:
        a.seek(offset)
        b.seek(offset)
        while True:
            chunk_a = a.read(1024 * 1024)
            chunk_b = b.read(1024 * 1024)
            if chunk_a != chunk_b:
                return False
            if not chunk_a:
                return True


def changed_ranges(left: bytes, right: bytes) -> list[tuple[int, int]]:
    assert len(left) == len(right)
    ranges = []
    offset = 0
    while offset < len(left):
        if left[offset] == right[offset]:
            offset += 1
            continue
        start = offset
        while offset < len(left) and left[offset] != right[offset]:
            offset += 1
        ranges.append((start, offset))
    return ranges


def ranges_outside(
    changed: list[tuple[int, int]], allowed: list[tuple[int, int]]
) -> list[tuple[int, int]]:
    outside = []
    for low, high in changed:
        cursor = low
        for permitted_low, permitted_high in allowed:
            if permitted_high <= cursor:
                continue
            if permitted_low >= high:
                break
            if permitted_low > cursor:
                outside.append((cursor, min(high, permitted_low)))
            cursor = max(cursor, permitted_high)
            if cursor >= high:
                break
        if cursor < high:
            outside.append((cursor, high))
    return outside


def rewrite_inf(template: Path, paths: list[Path], output: Path) -> None:
    ordered = iter(paths)
    source = template.read_text()
    lines = []
    for line in source.splitlines():
        if line.startswith("EFI_FILE_NAME"):
            line = f"EFI_FILE_NAME = {next(ordered)}"
        lines.append(line)
    try:
        next(ordered)
    except StopIteration:
        pass
    else:
        raise RuntimeError("FV INF has fewer EFI_FILE_NAME entries than inputs")
    output.write_text("\n".join(lines) + "\n")


def main() -> None:
    assert not (OUT / "boot-eud-off-route-private-r7.img").exists()
    assert not (OUT / "result.json").exists()

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "inputs").mkdir()
    (OUT / "sections").mkdir()

    p = load_packager()
    tool_paths = {name: Path(path) for name, path in p.TOOLS.items()}

    assert file_sha256(BASE_BOOT) == BASE_BOOT_SHA256
    assert BASE_BOOT.stat().st_size == BASE_BOOT_BYTES
    assert file_sha256(BASE_RECEIPT) == BASE_RECEIPT_SHA256
    assert file_sha256(RUNTIME_DTB) == NEW_DTB_SHA256
    assert RUNTIME_DTB.stat().st_size == NEW_DTB_BYTES
    assert file_sha256(BASE_SEC_INPUTS / "8AF09F13-44C5-96EC-1437-DD899CB5EE5D.ffs") == (
        "da8f6b97036aa734beb08104cf07932392d52a8d56bcee629ff810afe765266c"
    )

    inputs_to_snapshot = {
        BASE_BOOT,
        BASE_RECEIPT,
        BASE_FVMAIN,
        BASE_COMPACT,
        RUNTIME_DTB,
        RUNTIME_FAT_RECEIPT,
        PACKAGER,
        Path(__file__),
        BASE_SEC_INPUTS / "8AF09F13-44C5-96EC-1437-DD899CB5EE5D.ffs",
        BASE_SEC_INPUTS / "8AF09F13-44C5-96EC-1437-DD899CB5EE5D.efi",
        BASE_SEC_INPUTS / "8AF09F13-44C5-96EC-1437-DD899CB5EE5D.map",
    }
    inputs_to_snapshot.update(tool_paths.values())
    before = {str(path): file_sha256(path) for path in sorted(inputs_to_snapshot)}
    mount_before = Path("/proc/self/mountinfo").read_bytes()

    result = {
        "schema": "samurai-boot-dtb-carrier-v2",
        "passed": False,
        "scope": (
            "offline EUD-off DTB rebuild of boot-private-05; no device, SSH, or "
            "fastboot access"
        ),
        "output": str(OUT),
        "source_boot": {
            "path": str(BASE_BOOT),
            "bytes": BASE_BOOT.stat().st_size,
            "sha256": BASE_BOOT_SHA256,
        },
        "source_receipt": {
            "path": str(BASE_RECEIPT),
            "bytes": BASE_RECEIPT.stat().st_size,
            "sha256": BASE_RECEIPT_SHA256,
        },
        "old_native_DTB": {
            "sha256": BASE_DTB_SHA256,
            "bytes": BASE_DTB_BYTES,
        },
        "new_native_DTB": {
            "path": str(RUNTIME_DTB),
            "sha256": NEW_DTB_SHA256,
            "bytes": NEW_DTB_BYTES,
        },
        "fat_Image_sha256": FAT_IMAGE_SHA256,
        "BDS_EFI_sha256": BDS_EFI_SHA256,
        "max_used": PACKAGE_LIMIT,
        "parent_inputs_before": before,
        "commands": [],
    }
    save_json(OUT / "result.json", result)

    try:
        old = p.unpack(BASE_BOOT)
        assert old["used"] == PACKAGE_LIMIT
        assert old["ks"] > 0
        old_modules = p.raw_files(old["main"])
        assert len(old_modules) == 101
        old_dtb = p.fv(old["main"])[p.DT]["sections"]
        assert len(old_dtb) == 1 and old_dtb[0][0] == 0x19
        assert sha256(old_dtb[0][1]) == BASE_DTB_SHA256
        (OUT / "sections" / "source-DTB.raw").write_bytes(old_dtb[0][1])
        (OUT / "sections" / "new-DTB.raw").write_bytes(RUNTIME_DTB.read_bytes())

        extracted = p.extract_current(old["main"], OUT / "inputs")
        assert len(extracted) == 101
        assert file_sha256(extracted[p.BDS]) == (
            "a2cfd5ee459121e220574ae23fb873cb8089f4d722a45bf712c6a9ac23c5b4da"
        )
        assert file_sha256(extracted[p.DT]) == (
            "96d7a008d22deb60fdccf817ad8f0002f249e969388b5a08901a96b0a3b55fd8"
        )

        run_tool(
            result,
            "GenSec",
            str(tool_paths["GenSec"]),
            ["-s", "EFI_SECTION_RAW", "-o", OUT / "sections/DTB.raw", RUNTIME_DTB],
            "DTB-RAW",
        )
        run_tool(
            result,
            "GenFfs",
            str(tool_paths["GenFfs"]),
            [
                "-t",
                "EFI_FV_FILETYPE_FREEFORM",
                "-g",
                p.DT,
                "-o",
                extracted[p.DT],
                "-i",
                OUT / "sections/DTB.raw",
            ],
            "DTB-FFS",
        )
        rewrite_inf(
            BASE_FVMAIN,
            [extracted[row["guid"]] for row in p.m["main_FV"]["files"]],
            OUT / "FVMAIN.inf",
        )
        run_tool(
            result,
            "GenFv",
            str(tool_paths["GenFv"]),
            [
                "-g",
                p.m["main_FV"]["filesystem_guid"],
                "-i",
                OUT / "FVMAIN.inf",
                "-o",
                OUT / "main.Fv",
            ],
            "mainFV",
        )

        new_main = (OUT / "main.Fv").read_bytes()
        old_main = old["main"]
        old_raw = p.raw_files(old_main)
        new_raw = p.raw_files(new_main)
        assert list(old_raw) == list(new_raw)
        changed = [guid for guid in old_raw if old_raw[guid]["full"] != new_raw[guid]["full"]]
        assert changed == [p.DT], changed
        assert all(
            old_raw[guid]["full"] == new_raw[guid]["full"]
            for guid in old_raw
            if guid != p.DT
        )
        old_modules_parsed = p.fv(old_main)
        new_modules_parsed = p.fv(new_main)
        assert all(
            (
                old_modules_parsed[guid]["type"],
                old_modules_parsed[guid]["attrs"],
            )
            == (
                new_modules_parsed[guid]["type"],
                new_modules_parsed[guid]["attrs"],
            )
            for guid in old_raw
        )
        assert new_modules_parsed[p.DT]["sections"][0][1] == RUNTIME_DTB.read_bytes()
        assert old_raw[p.BDS]["full"] == new_raw[p.BDS]["full"]
        relocated = {
            guid: {
                "old_offset": old_raw[guid]["offset"],
                "new_offset": new_raw[guid]["offset"],
            }
            for guid in old_raw
            if old_raw[guid]["offset"] != new_raw[guid]["offset"]
        }
        result["main_verification"] = {
            "complete_FFS_count": len(new_raw),
            "changed_complete_FFS": changed,
            "other_100_complete_FFS_exact": True,
            "BDS_complete_FFS_exact": True,
            "DTB_section_type": "0x19_RAW",
            "DTB_payload_exact": True,
            "relocated_FFS_count": len(relocated),
            "relocated_FFS": relocated,
            "main_Fv_bytes": len(new_main),
            "main_Fv_sha256": sha256(new_main),
        }
        save_json(OUT / "result.json", result)

        run_tool(
            result,
            "GenSec",
            str(tool_paths["GenSec"]),
            [
                "-s",
                "EFI_SECTION_FIRMWARE_VOLUME_IMAGE",
                "-o",
                OUT / "main.fv.sec",
                OUT / "main.Fv",
            ],
            "FV-IMAGE",
        )
        run_tool(
            result,
            "GenSec",
            str(tool_paths["GenSec"]),
            ["--sectionalign", "8", "-o", OUT / "main.aligned", OUT / "main.fv.sec"],
            "align8",
        )
        run_tool(
            result,
            "LzmaCompress",
            str(tool_paths["LzmaCompress"]),
            ["-e", "-o", OUT / "main.lzma", OUT / "main.aligned"],
            "LZMA",
        )
        run_tool(
            result,
            "GenSec",
            str(tool_paths["GenSec"]),
            [
                "-s",
                "EFI_SECTION_GUID_DEFINED",
                "-g",
                p.m["compression"]["guided_guid"],
                "-r",
                "PROCESSING_REQUIRED",
                "-o",
                OUT / "main.guided",
                OUT / "main.lzma",
            ],
            "GUIDED",
        )
        run_tool(
            result,
            "GenFfs",
            str(tool_paths["GenFfs"]),
            [
                "-t",
                "EFI_FV_FILETYPE_FIRMWARE_VOLUME_IMAGE",
                "-g",
                p.CONTAINER,
                "-o",
                OUT / "container.ffs",
                "-i",
                OUT / "main.guided",
            ],
            "containerFFS",
        )

        for extension in (".ffs", ".efi", ".map"):
            name = p.SEC.upper() + extension
            shutil.copy2(BASE_SEC_INPUTS / name, OUT / "inputs" / name)
        rewrite_inf(
            BASE_COMPACT,
            [
                OUT / "inputs" / (p.SEC.upper() + ".ffs"),
                OUT / "container.ffs",
            ],
            OUT / "FVMAIN_COMPACT.inf",
        )
        run_tool(
            result,
            "GenFv",
            str(tool_paths["GenFv"]),
            [
                "-g",
                p.m["compact_FV"]["filesystem_guid"],
                "-i",
                OUT / "FVMAIN_COMPACT.inf",
                "-o",
                OUT / "compact.fd",
            ],
            "compactFD",
        )

        compact = (OUT / "compact.fd").read_bytes()
        old_compact = old["fd"]
        assert len(compact) == 7_340_032
        old_outer = p.raw_files(old_compact)
        new_outer = p.raw_files(compact)
        assert list(old_outer) == list(new_outer) == [p.SEC, p.CONTAINER]
        assert old_outer[p.SEC]["offset"] == new_outer[p.SEC]["offset"] == 0xFE8
        assert old_outer[p.SEC]["full"] == new_outer[p.SEC]["full"]
        assert old_outer[p.CONTAINER]["offset"] == new_outer[p.CONTAINER]["offset"]
        header_size = struct.unpack_from("<H", compact, 48)[0]
        assert compact[:header_size] == old_compact[:header_size]
        allowed_compact = sorted(
            [
                (
                    old_outer[p.CONTAINER]["offset"],
                    old_outer[p.CONTAINER]["offset"]
                    + len(old_outer[p.CONTAINER]["full"]),
                ),
                (
                    new_outer[p.CONTAINER]["offset"],
                    new_outer[p.CONTAINER]["offset"]
                    + len(new_outer[p.CONTAINER]["full"]),
                ),
            ]
        )
        outside_compact = ranges_outside(
            changed_ranges(old_compact, compact), allowed_compact
        )
        assert not outside_compact, outside_compact[:8]
        result["compact_verification"] = {
            "bytes": len(compact),
            "sha256": sha256(compact),
            "SEC_complete_FFS_exact": True,
            "SEC_offset": old_outer[p.SEC]["offset"],
            "container_offset_unchanged": True,
            "FV_header_exact": True,
            "changed_bytes_outside_container": 0,
        }
        save_json(OUT / "result.json", result)

        raw = old["shim"] + compact
        (OUT / "raw.bin").write_bytes(raw)
        os.utime(OUT / "raw.bin", ns=(GZIP_MTIME_NS, GZIP_MTIME_NS))
        run_tool(
            result,
            "gzip",
            str(tool_paths["gzip"]),
            ["-c"],
            "gzip",
            stdin_path=OUT / "raw.bin",
            stdout_path=OUT / "raw.gz",
        )
        gz = (OUT / "raw.gz").read_bytes()
        assert gz[:8] == old["gzip"][:8]
        assert gz[9] == old["gzip"][9]
        payload = gz + old["compat"]
        ks = len(payload)
        new_ram = 2048 + p.align(ks, 2048)
        used = 4096 + p.align(ks, 2048)

        compression_mode = "default"
        if used > PACKAGE_LIMIT:
            level9_path = OUT / "raw-level9.gz"
            run_tool(
                result,
                "gzip",
                str(tool_paths["gzip"]),
                ["-9", "-c"],
                "gzip-level9",
                stdin_path=OUT / "raw.bin",
                stdout_path=level9_path,
            )
            gz9 = level9_path.read_bytes()
            payload9 = gz9 + old["compat"]
            ks9 = len(payload9)
            used9 = 4096 + p.align(ks9, 2048)
            if used9 <= PACKAGE_LIMIT:
                gz, payload = gz9, payload9
                ks, new_ram, used = ks9, 2048 + p.align(ks9, 2048), used9
                compression_mode = "level9_fallback"

        result["geometry"] = {
            "max_used": PACKAGE_LIMIT,
            "kernel_payload_bytes": ks,
            "ram_offset": new_ram,
            "used": used,
            "fits": used <= PACKAGE_LIMIT,
            "compression_mode": compression_mode,
            "gzip_bytes": len(gz),
            "gzip_sha256": sha256(gz),
            "compat_bytes": len(old["compat"]),
            "compat_sha256": sha256(old["compat"]),
        }
        save_json(OUT / "result.json", result)
        assert used <= PACKAGE_LIMIT, (
            f"rebuilt payload does not fit: used={used}, limit={PACKAGE_LIMIT}"
        )

        header = bytearray(old["header"])
        header[8:12] = struct.pack("<I", ks)
        header[576:608] = p.id_value(payload, b"\n")
        target = OUT / "boot-eud-off-route-private-r7.img"
        with target.open("xb") as output, BASE_BOOT.open("rb") as source:
            output.write(header)
            output.write(payload)
            output.write(bytes(new_ram - 2048 - ks))
            output.write(old["ram_page"])
            assert output.tell() == used
            source.seek(used)
            shutil.copyfileobj(source, output, 1024 * 1024)
            output.flush()
            os.fsync(output.fileno())
        assert target.stat().st_size == BASE_BOOT_BYTES

        parsed = p.unpack(target)
        assert parsed["raw"][:144] == old["shim"]
        assert parsed["fd"] == compact
        assert parsed["compat"] == old["compat"]
        assert parsed["ram_page"] == old["ram_page"]
        written_raw = p.raw_files(parsed["main"])
        written_changed = [
            guid for guid in old_modules if old_modules[guid]["full"] != written_raw[guid]["full"]
        ]
        assert written_changed == [p.DT]
        assert all(
            old_modules[guid]["full"] == written_raw[guid]["full"]
            for guid in old_modules
            if guid != p.DT
        )
        assert p.fv(parsed["main"])[p.DT]["sections"][0][1] == RUNTIME_DTB.read_bytes()

        normalized_new = bytearray(parsed["header"])
        normalized_old = bytearray(old["header"])
        for item in (normalized_new, normalized_old):
            item[8:12] = b"\0" * 4
            item[576:608] = b"\0" * 32
        assert normalized_new == normalized_old
        assert equal_tail(target, BASE_BOOT, used)
        assert equal_tail(target, BASE_BOOT, PACKAGE_LIMIT)

        result.update(
            passed=True,
            boot_path=str(target),
            boot_sha256=file_sha256(target),
            boot_bytes=target.stat().st_size,
            native_DTB_sha256=NEW_DTB_SHA256,
            native_DTB_bytes=NEW_DTB_BYTES,
            new_kernel_size=ks,
            new_used=used,
            geometry_passed=True,
            only_embedded_DTB_payload_changed=True,
            main_FFS_changed=[p.DT],
            other_main_FFS_exact=True,
            compact_SEC_exact=True,
            shim_exact=True,
            compat_exact=True,
            ramdisk_exact=True,
            boot_header_only_size_and_ID_changed=True,
            absolute_tail_exact=True,
            written_boot_fully_reparsed=True,
            no_device_or_deployment=True,
            fat_Image_untouched=True,
        )
        result["written_main_verification"] = {
            "complete_FFS_count": len(written_raw),
            "changed_complete_FFS": written_changed,
            "other_100_complete_FFS_exact": True,
            "new_DTB_payload_exact": True,
        }
        result["written_boot"] = {
            "path": str(target),
            "bytes": target.stat().st_size,
            "sha256": file_sha256(target),
            "header_sha256": sha256(parsed["header"]),
            "payload_bytes": len(parsed["payload"]),
            "payload_sha256": sha256(parsed["payload"]),
            "raw_bytes": len(parsed["raw"]),
            "raw_sha256": sha256(parsed["raw"]),
            "compact_fd_sha256": sha256(parsed["fd"]),
            "main_Fv_sha256": sha256(parsed["main"]),
        }
    except BaseException as error:
        result.update(error=repr(error), traceback=traceback.format_exc())

    after = {str(path): file_sha256(path) for path in sorted(inputs_to_snapshot)}
    result.update(
        parent_inputs_after=after,
        parent_inputs_unchanged=before == after,
        parent_mountinfo_unchanged=mount_before == Path("/proc/self/mountinfo").read_bytes(),
        fat_receipt={
            "path": str(RUNTIME_FAT_RECEIPT),
            "sha256": file_sha256(RUNTIME_FAT_RECEIPT),
            "expected_sha256": FAT_RECEIPT_SHA256,
        },
    )
    result["passed"] = (
        result["passed"]
        and result["parent_inputs_unchanged"]
        and result["parent_mountinfo_unchanged"]
        and file_sha256(RUNTIME_FAT_RECEIPT) == FAT_RECEIPT_SHA256
    )
    save_json(OUT / "result.json", result)
    print(
        json.dumps(
            {
                key: result.get(key)
                for key in (
                    "passed",
                    "boot_sha256",
                    "new_native_DTB",
                    "new_kernel_size",
                    "new_used",
                    "error",
                )
            },
            indent=2,
        )
    )
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
