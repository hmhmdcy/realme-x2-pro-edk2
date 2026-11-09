#!/usr/bin/env python3
"""Independently verify the signed v7.3.1 Bluetooth host module package."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import struct
import subprocess
import zlib


EXPECTED = {
    "package": "a4cbe10a1a7a5b6e13ba01bf2a27e64663a0e290c2fd168c54e2b17f44a4be5e",
    "index": "5d4f43e3f99eabb74d9eff60e94402df05608c1d1065f420a24408fb251c34ae",
    "manifest": "7a12f03f21b03a538448fa5a6bbc1cab8d82f5a00c3c345aa0ae5ad9eae1fbf3",
    "public_key": "dbfa32c3c97d5624e558547ec6e47725f77a1f4f0569455288f79ca66269bbc3",
    "symvers": "77338912db077834f4e7762ed49638a64fe5e15defdc9cccc0482f1396cd2583",
    "release": "7.3.1-rmx1931-samurai-v731",
    "modules": {
        "bnep.ko": "aa2e7affa0bc7238a61a0bdfc190be533f6382ea21eaebf88b3419301a412b74",
        "uhid.ko": "a5e72e3ed257c978e35fe12dcb18784d790f96c059c37cc09576b813d57ceea0",
        "uinput.ko": "d5a94b699e33aef2835a0ba5e2f419574f7da3c643ade9d8f2ed4be781029bbb",
    },
    "payload": {
        "bnep.ko": (
            "usr/lib/modules/7.3.1-rmx1931-samurai-v731/"
            "kernel/net/bluetooth/bnep/bnep.ko"
        ),
        "uhid.ko": (
            "usr/lib/modules/7.3.1-rmx1931-samurai-v731/"
            "kernel/drivers/hid/uhid.ko"
        ),
        "uinput.ko": (
            "usr/lib/modules/7.3.1-rmx1931-samurai-v731/"
            "kernel/drivers/input/misc/uinput.ko"
        ),
    },
}
PACKAGE_NAME = "samurai-bluetooth-host"
PACKAGE_VERSION = "0.1.0-r0"
SOURCE_DATE_EPOCH = 1794216000
VERMAGIC = EXPECTED["release"] + " SMP preempt mod_unload aarch64"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256(path.read_bytes())


def parse_config(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("# CONFIG_") and line.endswith(" is not set"):
            result[line[2:-11]] = "n"
        elif line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            result[key] = value
    return result


def semantic_config_delta(before: dict[str, str],
                          after: dict[str, str]) -> dict[str, list[str]]:
    def normalized(value: str | None) -> str:
        return "n" if value in (None, "n") else value

    changes = {}
    for key in sorted(set(before) | set(after)):
        old = normalized(before.get(key))
        new = normalized(after.get(key))
        if old != new:
            changes[key] = [old, new]
    return changes


def module_view(raw: bytes, expected_name: str) -> dict:
    require(raw[:6] == b"\x7fELF\x02\x01", "expected little-endian ELF64")
    require(
        struct.unpack_from("<HH", raw, 16) == (1, 183),
        "expected AArch64 relocatable module",
    )
    section_offset = struct.unpack_from("<Q", raw, 40)[0]
    section_size, section_count, names_index = struct.unpack_from(
        "<HHH", raw, 58
    )
    require(
        section_size == 64
        and names_index < section_count
        and section_offset + section_size * section_count <= len(raw),
        "invalid section table",
    )
    rows = [
        struct.unpack_from(
            "<IIQQQQIIQQ", raw, section_offset + index * section_size
        )
        for index in range(section_count)
    ]
    names = raw[rows[names_index][4]:rows[names_index][4] + rows[names_index][5]]
    sections: dict[str, bytes] = {}
    for row in rows:
        label = names[row[0]:].split(b"\0", 1)[0].decode("ascii")
        if row[1] != 8:
            require(row[4] + row[5] <= len(raw), "section outside artifact")
            sections[label] = raw[row[4]:row[4] + row[5]]
    require(".modinfo" in sections, "missing .modinfo")
    fields: dict[str, list[str]] = {}
    for item in sections[".modinfo"].split(b"\0"):
        if b"=" in item:
            key, value = item.split(b"=", 1)
            fields.setdefault(key.decode(), []).append(value.decode())
    require(fields.get("name") == [expected_name], "wrong module name")
    require(fields.get("intree") == ["Y"], "missing intree=Y")
    require(fields.get("vermagic") == [VERMAGIC], "wrong vermagic")
    symtab = next(row for row in rows if row[1] == 2)
    require(
        symtab[9] == 24
        and symtab[5] % 24 == 0
        and symtab[6] < section_count,
        "invalid symbol table",
    )
    strings = raw[rows[symtab[6]][4]:rows[symtab[6]][4] + rows[symtab[6]][5]]
    imports = set()
    for offset in range(symtab[4], symtab[4] + symtab[5], 24):
        name_offset, info, _other, index, _value, _length = (
            struct.unpack_from("<IBBHQQ", raw, offset)
        )
        if index == 0 and info >> 4 in (1, 2) and name_offset:
            imports.add(
                strings[name_offset:].split(b"\0", 1)[0].decode()
            )
    require(imports, "module has no imported symbols")
    require(".note.gnu.build-id" in sections, "missing build-id")
    ordered = sorted(imports)
    return {
        "name": expected_name,
        "bytes": len(raw),
        "sha256": sha256(raw),
        "vermagic": fields["vermagic"][0],
        "intree": "Y",
        "depends": fields.get("depends", [""])[0],
        "build_id_note_sha256": sha256(sections[".note.gnu.build-id"]),
        "imports_sha256": sha256(
            ("\n".join(ordered) + "\n").encode("utf-8")
        ),
        "imported_symbols": ordered,
    }


def run(command: list[str | Path], log: Path) -> str:
    result = subprocess.run(
        [str(item) for item in command],
        capture_output=True,
        check=False,
    )
    log.write_bytes(result.stdout + result.stderr)
    require(result.returncode == 0, f"command failed: {Path(command[0]).name}")
    return (result.stdout + result.stderr).decode("utf-8", "replace")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-dir", required=True, type=Path)
    parser.add_argument("--module-dir", required=True, type=Path)
    parser.add_argument("--build-dir", required=True, type=Path)
    parser.add_argument("--symvers", required=True, type=Path)
    parser.add_argument("--apk", required=True, type=Path)
    parser.add_argument("--build-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    require(os.name == "posix" and os.geteuid() == 0, "run as root in Linux")
    require(
        args.build_root.is_absolute()
        and not args.build_root.exists()
        and not str(args.build_root).startswith("/mnt/"),
        "fresh Linux validation root required",
    )
    args.build_root.mkdir(parents=True, mode=0o700)
    candidate = args.candidate_dir.resolve()
    package = candidate / f"{PACKAGE_NAME}-{PACKAGE_VERSION}.apk"
    index = candidate / "packages.adb"
    manifest_path = candidate / "package-manifest.json"
    public_key = candidate / "samurai-linux-203.rsa.pub"
    for path, expected_name in [
        (package, "package"),
        (index, "index"),
        (manifest_path, "manifest"),
        (public_key, "public_key"),
    ]:
        require(path.is_file(), f"{expected_name} missing")
        require(
            sha256_path(path) == EXPECTED[expected_name],
            f"{expected_name} hash mismatch",
        )
    require(sha256_path(args.symvers) == EXPECTED["symvers"],
            "Module.symvers mismatch")

    release = (args.build_dir / "include/config/kernel.release").read_text(
        encoding="utf-8"
    ).strip()
    require(release == EXPECTED["release"], "kernel release mismatch")
    before = parse_config(args.build_dir / ".config.before-bnep-uhid")
    after = parse_config(args.build_dir / ".config")
    require(
        semantic_config_delta(before, after)
        == {
            "CONFIG_BT_BNEP": ["n", "m"],
            "CONFIG_INPUT_UINPUT": ["n", "m"],
            "CONFIG_UHID": ["n", "m"],
        },
        "unexpected semantic config delta",
    )
    build_log = (args.build_dir / "module-build.log").read_text(
        encoding="utf-8", errors="replace"
    )
    require("warning:" not in build_log.lower(), "build warning present")
    require("error:" not in build_log.lower(), "build error present")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    require(manifest.get("schema") == "samurai-bluetooth-host-v1", "schema")
    require(manifest.get("package") == package.name, "package name")
    require(manifest.get("sha256") == EXPECTED["package"], "manifest package hash")
    require(
        manifest.get("index_sha256") == EXPECTED["index"],
        "manifest index hash",
    )
    require(manifest.get("kernel_release") == EXPECTED["release"], "manifest release")
    require(manifest.get("device_installed") is False, "install claim")
    require(manifest.get("modules_loaded") is False, "load claim")
    require(
        manifest.get("hardware_pan_hid_verified") is False,
        "hardware claim",
    )
    require(
        manifest.get("install_hooks_present") is False
        and manifest.get("service_files_present") is False
        and manifest.get("modules_load_config_added") is False,
        "unexpected package-side integration",
    )
    available = {
        line.split()[1]
        for line in args.symvers.read_text(encoding="utf-8").splitlines()
        if line.split()
    }
    modules: dict[str, bytes] = {}
    for filename, expected_hash in EXPECTED["modules"].items():
        path = args.module_dir / filename
        require(path.is_file(), f"{filename} missing")
        raw = path.read_bytes()
        require(sha256(raw) == expected_hash, f"{filename} hash mismatch")
        view = module_view(raw, Path(filename).stem)
        require(view["depends"] == "", f"{filename} has dependencies")
        require(
            set(view["imported_symbols"]) <= available,
            f"{filename} has unresolved imports",
        )
        record = manifest["modules"][Path(filename).stem]
        for field in [
            "bytes",
            "sha256",
            "vermagic",
            "intree",
            "depends",
            "build_id_note_sha256",
            "imports_sha256",
            "imported_symbols",
        ]:
            require(record.get(field) == view[field], f"{filename}.{field}")
        modules[filename] = raw

    run(
        [args.apk, "--keys-dir", candidate, "verify", package],
        args.build_root / "verify-package.log",
    )
    run(
        [args.apk, "--keys-dir", candidate, "verify", index],
        args.build_root / "verify-index.log",
    )
    dump = run(
        [args.apk, "adbdump", package],
        args.build_root / "adbdump.log",
    )
    require(
        f"  name: {PACKAGE_NAME}\n" in dump
        and f"  version: {PACKAGE_VERSION}\n" in dump
        and "  arch: aarch64\n" in dump,
        "signed package identity",
    )
    require(
        all(token not in dump for token in ["scripts:", "triggers:", "replaces:"]),
        "unexpected package hooks",
    )
    dependencies = re.search(
        r"^  depends:(?: #[^\n]*)?\n((?:    - .+\n)+)", dump, re.M
    )
    require(
        dependencies
        and dependencies.group(1).splitlines() == ["    - bluez", "    - kmod"],
        "unexpected signed dependencies",
    )

    directories: list[str | None] = [None]
    files: dict[tuple[int, int], dict] = {}
    directory_index = 0
    file_index = 0
    for line in dump.splitlines():
        match = re.match(r"^  - name: (.+)$", line)
        if match:
            directory_index += 1
            directories.append(match[1])
            file_index = 0
        match = re.match(r"^      - name: (.+)$", line)
        if match:
            file_index += 1
            files[(directory_index, file_index)] = {
                "path": directories[directory_index] + "/" + match[1]
            }
        for pattern, key, convert in [
            (r"^          mode: ([0-7]+)$", "mode", lambda value: int(value, 8)),
            (r"^        size: (\d+)$", "size", int),
            (r"^        hash: ([a-f0-9]{64})$", "sha256", str),
        ]:
            match = re.match(pattern, line)
            if match:
                files[(directory_index, file_index)][key] = convert(match[1])
    expected_by_path = {
        EXPECTED["payload"][filename]: modules[filename]
        for filename in modules
    }
    require(
        len(files) == 3
        and {row["path"] for row in files.values()} == set(expected_by_path),
        "unexpected signed file inventory",
    )
    first_bytes = package.read_bytes()
    require(
        first_bytes[:6] == b"ADBc\x01\x09",
        "expected APKv3 deflate package",
    )
    raw = zlib.decompress(first_bytes[6:], -15)
    require(raw[:8] == b"ADB.pckg", "unexpected package schema")
    offset = 8
    seen: set[tuple[int, int]] = set()
    while offset < len(raw):
        header = struct.unpack_from("<I", raw, offset)[0]
        length, kind = header & 0x3FFFFFFF, header >> 30
        require(
            length >= 4
            and offset + length <= len(raw)
            and kind in [0, 1, 2],
            "invalid APK data block",
        )
        body = raw[offset + 4:offset + length]
        if kind == 2:
            key = struct.unpack_from("<II", body, 0)
            require(key in files and key not in seen, "duplicate payload")
            seen.add(key)
            row, payload = files[key], body[8:]
            original = expected_by_path[row["path"]]
            require(
                payload == original
                and len(payload) == row["size"]
                and sha256(payload) == row["sha256"]
                and row["mode"] == 0o644,
                "signed payload/mode mismatch",
            )
        end = offset + length
        offset = (end + 7) & ~7
        require(not any(raw[end:offset]), "nonzero APK block padding")
    require(offset == len(raw) and len(seen) == 3, "payload readback incomplete")

    root = args.build_root / "isolated-root"
    root.mkdir()
    database = root / "lib/apk/db"
    database.mkdir(parents=True)
    fixture = "\n\n".join(
        "C:Q1"
        + base64.b64encode(
            hashlib.sha1(("fixture-" + name).encode()).digest()
        ).decode()
        + f"\nP:{name}\nV:0\nA:aarch64\nS:0\nI:0\n"
        + "T:Metadata-only offline payload-test dependency fixture"
        for name in ["bluez", "kmod"]
    ) + "\n\n"
    (database / "installed").write_text(fixture, encoding="utf-8")
    (root / "etc/apk").mkdir(parents=True)
    (root / "etc/apk/world").write_text("bluez\nkmod\n", encoding="utf-8")
    run(
        [
            args.apk,
            "--root",
            root,
            "--initdb",
            "--arch",
            "aarch64",
            "--keys-dir",
            candidate,
            "--no-scripts",
            "--no-network",
            "--no-commit-hooks",
            "add",
            package,
        ],
        args.build_root / "isolated-install.log",
    )
    actual_files = {
        str(path.relative_to(root))
        for path in (root / "usr").rglob("*")
        if path.is_file()
    }
    require(actual_files == set(expected_by_path), "unexpected extracted files")
    require(
        not any(path.is_symlink() for path in root.rglob("*")),
        "unexpected symlink",
    )
    file_checks = []
    for relative, original in sorted(expected_by_path.items()):
        extracted = root / relative
        info = extracted.stat()
        require(
            extracted.read_bytes() == original
            and stat.S_IMODE(info.st_mode) == 0o644
            and info.st_uid == info.st_gid == 0,
            "extracted bytes/mode/uid/gid mismatch",
        )
        owner = run(
            [args.apk, "--root", root, "info", "-W", "/" + relative],
            args.build_root / ("owner-" + extracted.name + ".log"),
        )
        require(f"{PACKAGE_NAME}-{PACKAGE_VERSION}" in owner, "owner mismatch")
        file_checks.append({
            "path": relative,
            "bytes": len(original),
            "sha256": sha256(original),
            "mode": 0o644,
            "uid": 0,
            "gid": 0,
        })
    records = [
        row
        for row in (database / "installed").read_text(encoding="utf-8").split("\n\n")
        if f"\nP:{PACKAGE_NAME}\n" in "\n" + row + "\n"
    ]
    require(
        len(records) == 1
        and f"\nV:{PACKAGE_VERSION}\n" in "\n" + records[0] + "\n",
        "installed version mismatch",
    )
    failure_flags = re.findall(r"^f:(.*)$", records[0], re.M)
    require(
        not any(flag in "".join(failure_flags) for flag in "fsx"),
        "package failure flags present",
    )
    require(
        package.read_bytes() == first_bytes,
        "package changed during verification",
    )
    report = {
        "schema": "samurai-bluetooth-host-verifier-v1",
        "passed": True,
        "package": package.name,
        "package_bytes": len(first_bytes),
        "package_sha256": sha256(first_bytes),
        "index_sha256": EXPECTED["index"],
        "manifest_sha256": EXPECTED["manifest"],
        "package_signature_verified": True,
        "index_signature_verified": True,
        "exact_three_module_inventory_verified": True,
        "all_signed_data_blocks_modes_and_hashes_verified": True,
        "isolated_apk_install_passed": True,
        "isolated_apk_owner_and_version_verified": True,
        "isolated_apk_failure_flags": failure_flags,
        "files": file_checks,
        "signed_dependencies": ["bluez", "kmod"],
        "no_package_scripts_triggers_or_replaces": True,
        "metadata_only_dependency_fixtures_used": True,
        "device_or_original_rootfs_install_performed": False,
        "modules_loaded_or_unloaded": False,
        "hardware_pan_hid_verified": False,
        "source_date_epoch": SOURCE_DATE_EPOCH,
        "scope": (
            "Offline signature, payload and isolated-install verification "
            "only. PAN, HID pairing, module loading, recovery and cold boot "
            "remain unverified."
        ),
    }
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    require(
        package.read_bytes() == first_bytes,
        "package changed after report write",
    )
    print(json.dumps({
        "passed": report["passed"],
        "package": report["package"],
        "package_sha256": report["package_sha256"],
        "isolated_apk_install_passed": report["isolated_apk_install_passed"],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
