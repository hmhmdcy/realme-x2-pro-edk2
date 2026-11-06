#!/usr/bin/env python3
"""Build only BdsDxe with the production SAMURAI_ENABLE_EUD option removed."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import struct
import subprocess
import sys
from pathlib import Path


REPO = Path("/home/cy122/edk2-samurai/repo")
BUILD = REPO / "workspace/Build/samurai/RELEASE_GCC5/AARCH64"
PLATFORM = BUILD / "Platform/RenegadePkg/Library/PlatformBootManagerLib/PlatformBootManagerLib"
BDS = BUILD / "MdeModulePkg/Universal/BdsDxe/BdsDxe"
SOURCE = REPO / "Platform/RenegadePkg/Library/PlatformBootManagerLib/PlatformBm.c"
OUTPUT = Path(
    "/mnt/e/edk2-samurai-out/standard-arm64-v731/edk2-source-rebuild"
)
STAGING = Path("/home/cy122/edk2-samurai-build/bds-source-rebuild")
CC = Path("/usr/bin/aarch64-linux-gnu-gcc")
AR = Path("/usr/bin/aarch64-linux-gnu-gcc-ar")
GENFW = REPO / "Common/edk2/BaseTools/Source/C/bin/GenFw"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def make_variables(module: Path) -> dict[str, str]:
    variables = {
        "ARCHCC_FLAGS": "",
        "SLINK_FLAGS": "",
        "EDK_TOOLS_PATH": str(REPO / "Common/edk2/BaseTools"),
    }
    for line in (module / "GNUmakefile").read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([A-Za-z_][A-Za-z_0-9]*)\s*=\s*(.*)", line)
        if match:
            variables[match.group(1)] = match.group(2)
    return variables


def expand(rule: str, variables: dict[str, str]) -> str:
    for _ in range(20):
        if "$(" not in rule:
            break

        def replace(match: re.Match[str]) -> str:
            name = match.group(1)
            if name not in variables:
                raise SystemExit(f"unresolved make variable: {name}")
            return variables[name]

        rule = re.sub(r"\$\(([^)]+)\)", replace, rule)
    if "$" in rule:
        raise SystemExit(f"unresolved make syntax: {rule}")
    return rule


def filter_define(words: list[str]) -> list[str]:
    return [word for word in words if word != "-DSAMURAI_ENABLE_EUD"]


def run(argv: list[str], cwd: Path, log: Path) -> None:
    print("+", " ".join(shlex.quote(word) for word in argv), flush=True)
    environment = dict(os.environ)
    environment["PATH"] = "/usr/bin:/bin"
    for name in ("GCC_EXEC_PREFIX", "COMPILER_PATH", "LIBRARY_PATH"):
        environment.pop(name, None)
    with log.open("wb") as output:
        result = subprocess.run(
            argv, cwd=cwd, env=environment, stdout=output,
            stderr=subprocess.STDOUT, timeout=600,
        )
    if result.returncode:
        raise SystemExit(f"command failed: {' '.join(argv)}; see {log}")


def pe_info(data: bytes) -> dict[str, object]:
    if data[:2] != b"MZ":
        raise SystemExit("not a PE image")
    pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe_offset:pe_offset + 4] != b"PE\0\0":
        raise SystemExit("missing PE signature")
    machine = struct.unpack_from("<H", data, pe_offset + 4)[0]
    if machine != 0xAA64:
        raise SystemExit(f"unexpected PE machine: 0x{machine:04x}")
    return {
        "bytes": len(data),
        "sha256": digest(data),
        "machine": "0xaa64",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    source = args.source
    output = args.output
    if not args.execute:
        print(json.dumps({
            "source": str(source),
            "source_sha256": digest(source.read_bytes()),
            "output": str(output),
            "default_has_eud_define": "-DSAMURAI_ENABLE_EUD" in
                (PLATFORM / "OUTPUT/cc_resp.txt").read_text(encoding="utf-8"),
        }, indent=2))
        return 0
    if output.exists():
        raise SystemExit(f"refusing to replace {output}")
    output.mkdir(parents=True)
    if STAGING.exists():
        shutil.rmtree(STAGING)
    STAGING.mkdir(parents=True)
    work = STAGING

    source_copy = work / "PlatformBm.c"
    shutil.copy2(source, source_copy)
    response = filter_define(
        shlex.split((PLATFORM / "OUTPUT/cc_resp.txt").read_text(encoding="utf-8"))
    )
    (work / "cc_resp.txt").write_text(" ".join(response) + "\n", encoding="utf-8")

    object_path = work / "PlatformBm.obj"
    run([
        str(CC), "-MMD", "-MF", str(work / "PlatformBm.obj.deps"),
        f"@{work / 'cc_resp.txt'}", "-c", "-o", str(object_path),
        str(source_copy),
    ], PLATFORM, work / "compile.log")

    archive = work / "PlatformBootManagerLib.lib"
    archive.unlink(missing_ok=True)
    run([str(AR), "cr", str(archive), str(object_path)],
        PLATFORM, work / "archive.log")

    libraries = [
        line for line in (BDS / "OUTPUT/static_library_files.lst").read_text(
            encoding="utf-8"
        ).splitlines() if line.strip()
    ]
    original_platform = str(
        PLATFORM / "OUTPUT/PlatformBootManagerLib.lib"
    )
    matches = [index for index, value in enumerate(libraries)
               if value == original_platform]
    if len(matches) != 1:
        raise SystemExit(f"unexpected platform library entries: {matches}")
    libraries[matches[0]] = str(archive)
    library_list = work / "static_library_files.lst"
    library_list.write_text("\n".join(libraries) + "\n", encoding="utf-8")

    variables = make_variables(BDS)
    dllink_flags = shlex.split(expand(variables["DLINK_FLAGS"], variables))
    cc_flags = filter_define(shlex.split(expand(variables["CC_FLAGS"], variables)))
    dlink2_flags = shlex.split(expand(variables["DLINK2_FLAGS"], variables))
    map_path = BDS / "DEBUG/BdsDxe.map"
    output_map = work / "BdsDxe.map"
    dllink_flags = [
        value.replace(str(map_path), str(output_map))
        for value in dllink_flags
    ]
    dll = work / "BdsDxe.dll"
    run([
        str(CC), "-o", str(dll), *dllink_flags,
        "-Wl,--start-group", f"@{library_list}", "-Wl,--end-group",
        *cc_flags, *dlink2_flags,
    ], BDS, work / "link.log")

    efi = work / "BdsDxe.efi"
    run([str(GENFW), "-e", "DXE_DRIVER", "-o", str(efi), str(dll)],
        BDS, work / "genfw.log")
    data = efi.read_bytes()
    if "earlycon=eud".encode("utf-16le") in data:
        raise SystemExit("EUD earlycon is still present in the BdsDxe image")

    result = {
        "passed": True,
        "source": str(source),
        "source_sha256": digest(source.read_bytes()),
        "compiled_source_sha256": digest(source_copy.read_bytes()),
        "SAMURAI_ENABLE_EUD_removed": True,
        "BdsDxe": pe_info(data),
        "platform_object_sha256": digest(object_path.read_bytes()),
        "platform_archive_sha256": digest(archive.read_bytes()),
        "staging": str(work),
        "shared_build_tree_modified": False,
    }
    write_json(output / "result.json", result)
    for name in (
        "BdsDxe.efi", "BdsDxe.dll", "BdsDxe.map", "compile.log",
        "archive.log", "link.log", "genfw.log",
    ):
        shutil.copy2(work / name, output / name)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
