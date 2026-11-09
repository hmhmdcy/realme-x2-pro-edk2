#!/usr/bin/env python3
"""Package and sign the v7.3.1 mainline Bluetooth host modules.

The three modules are built from the already deployed v7.3.1 kernel tree:
BNEP for Bluetooth PAN, UHID and uinput for BlueZ HID.
This tool never builds or loads a module, edits the running system, uses the
device, or writes a private signing key.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import struct
import subprocess


RELEASE = "7.3.1-rmx1931-samurai-v731"
VERMAGIC = RELEASE + " SMP preempt mod_unload aarch64"
SOURCE_COMMIT = "824dc0a56143d8bf1cc1d20adb877abced48b336"
SOURCE_DATE_EPOCH = 1794216000
PACKAGE_NAME = "samurai-bluetooth-host"
PACKAGE_VERSION = "0.1.0-r0"
MODULES = {
    "bnep": {
        "build_path": "net/bluetooth/bnep/bnep.ko",
        "payload_path": (
            f"usr/lib/modules/{RELEASE}/kernel/net/bluetooth/bnep/bnep.ko"
        ),
        "purpose": "Bluetooth PAN/BNEP",
    },
    "uhid": {
        "build_path": "drivers/hid/uhid.ko",
        "payload_path": (
            f"usr/lib/modules/{RELEASE}/kernel/drivers/hid/uhid.ko"
        ),
        "purpose": "BlueZ userspace HID transport",
    },
    "uinput": {
        "build_path": "drivers/input/misc/uinput.ko",
        "payload_path": (
            f"usr/lib/modules/{RELEASE}/kernel/drivers/input/misc/uinput.ko"
        ),
        "purpose": "userspace input injection used by BlueZ HID",
    },
}
EXPECTED_CONFIG = {
    "CONFIG_BT_BNEP": "m",
    "CONFIG_INPUT_UINPUT": "m",
    "CONFIG_UHID": "m",
}


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
        "sha256": sha256(raw),
        "bytes": len(raw),
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
    parser.add_argument("--build-dir", required=True, type=Path)
    parser.add_argument("--module-dir", required=True, type=Path)
    parser.add_argument("--symvers", required=True, type=Path)
    parser.add_argument("--apk", required=True, type=Path)
    parser.add_argument("--sign-key", required=True, type=Path)
    parser.add_argument("--verification-keys", required=True, type=Path)
    parser.add_argument("--build-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    require(os.name == "posix" and os.geteuid() == 0, "run as root in Linux")
    require(
        args.build_root.is_absolute()
        and not args.build_root.exists()
        and not str(args.build_root).startswith("/mnt/"),
        "fresh Linux build root required",
    )
    require(
        args.output.is_absolute() and not args.output.exists(),
        "fresh output directory required",
    )
    require(args.apk.is_file(), "apk.static is missing")
    require(args.sign_key.is_file(), "signing key is missing")
    require(args.verification_keys.is_dir(), "verification key directory missing")
    require(
        (args.verification_keys / (args.sign_key.name + ".pub")).is_file(),
        "matching public verification key missing",
    )

    build_dir = args.build_dir.resolve()
    module_dir = args.module_dir.resolve()
    symvers = args.symvers.resolve()
    require(build_dir.is_dir(), "build directory missing")
    require(module_dir.is_dir(), "stripped module directory missing")
    require(symvers.is_file(), "Module.symvers missing")

    release = (build_dir / "include/config/kernel.release").read_text(
        encoding="utf-8"
    ).strip()
    require(release == RELEASE, f"unexpected kernel release: {release}")
    before = parse_config(build_dir / ".config.before-bnep-uhid")
    after = parse_config(build_dir / ".config")
    delta = semantic_config_delta(before, after)
    require(delta == {
        key: ["n", value] for key, value in EXPECTED_CONFIG.items()
    }, f"unexpected config delta: {delta}")
    for key, value in EXPECTED_CONFIG.items():
        require(after.get(key) == value, f"{key} is not {value}")

    build_log_path = build_dir / "module-build.log"
    require(build_log_path.is_file(), "module build log missing")
    build_log = build_log_path.read_text(encoding="utf-8", errors="replace")
    require("warning:" not in build_log.lower(), "build log contains warning")
    require("error:" not in build_log.lower(), "build log contains error")
    for name, entry in MODULES.items():
        require(
            f"LD [M]  {entry['build_path']}" in build_log,
            f"build log lacks {name} link step",
        )

    available = {
        line.split()[1]
        for line in symvers.read_text(encoding="utf-8").splitlines()
        if line.split()
    }
    require(available, "empty Module.symvers")
    module_records: dict[str, dict] = {}
    payloads: dict[str, bytes] = {}
    for name, entry in MODULES.items():
        unstripped = build_dir / entry["build_path"]
        stripped = module_dir / f"{name}.ko"
        require(unstripped.is_file(), f"unstripped {name}.ko missing")
        require(stripped.is_file(), f"stripped {name}.ko missing")
        unstripped_view = module_view(unstripped.read_bytes(), name)
        stripped_view = module_view(stripped.read_bytes(), name)
        for field in [
            "vermagic",
            "intree",
            "depends",
            "build_id_note_sha256",
            "imports_sha256",
            "imported_symbols",
        ]:
            require(
                unstripped_view[field] == stripped_view[field],
                f"strip changed {name}.{field}",
            )
        require(stripped_view["depends"] == "", f"{name} has dependencies")
        missing = set(stripped_view["imported_symbols"]) - available
        require(not missing, f"{name} unresolved imports: {sorted(missing)}")
        module_records[name] = {
            **stripped_view,
            "purpose": entry["purpose"],
            "payload_path": entry["payload_path"],
            "source_path": entry["build_path"],
        }
        payloads[entry["payload_path"]] = stripped.read_bytes()

    args.build_root.mkdir(parents=True, mode=0o700)
    args.output.mkdir(parents=True, mode=0o700)
    payload = args.build_root / "payload"
    payload.mkdir()
    for relative, raw in payloads.items():
        target = payload / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        target.chmod(0o644)
    for path in [*payload.rglob("*"), payload]:
        os.chown(path, 0, 0)
        os.utime(path, (SOURCE_DATE_EPOCH, SOURCE_DATE_EPOCH))

    metadata = {
        "name": PACKAGE_NAME,
        "version": PACKAGE_VERSION,
        "arch": "aarch64",
        "license": "GPL-2.0-only",
        "origin": PACKAGE_NAME,
        "description": (
            "Mainline Linux v7.3.1 Bluetooth PAN and HID host modules "
            "for Realme X2 Pro"
        ),
        "maintainer": "Realme X2 Pro Linux port",
        "url": "https://github.com/hmhmdcy/edk2-realme-x2-pro",
        "depends": "bluez kmod",
        "build-time": str(SOURCE_DATE_EPOCH),
    }
    package = args.output / f"{PACKAGE_NAME}-{PACKAGE_VERSION}.apk"
    command: list[str | Path] = [
        args.apk,
        "mkpkg",
        "--compat",
        "3.0.0",
        "--compression",
        "deflate:9",
        "--files",
        payload,
        "--sign-key",
        args.sign_key,
        "--output",
        package,
    ]
    for key, value in sorted(metadata.items()):
        command += ["--info", f"{key}:{value}"]
    run(command, args.build_root / "mkpkg.log")
    run(
        [args.apk, "--keys-dir", args.verification_keys, "verify", package],
        args.build_root / "verify-package.log",
    )

    index = args.output / "packages.adb"
    run(
        [
            args.apk,
            "--keys-dir",
            args.verification_keys,
            "mkndx",
            "--compression",
            "deflate:9",
            "--sign-key",
            args.sign_key,
            "--pkgname-spec",
            "${name}-${version}.apk",
            "--description",
            "Realme X2 Pro Bluetooth host modules",
            "--output",
            index,
            package,
        ],
        args.build_root / "mkndx.log",
    )
    run(
        [args.apk, "--keys-dir", args.verification_keys, "verify", index],
        args.build_root / "verify-index.log",
    )

    public_key = args.verification_keys / (args.sign_key.name + ".pub")
    (args.output / public_key.name).write_bytes(public_key.read_bytes())
    manifest = {
        "schema": "samurai-bluetooth-host-v1",
        "package": package.name,
        "version": PACKAGE_VERSION,
        "sha256": sha256_path(package),
        "bytes": package.stat().st_size,
        "index_sha256": sha256_path(index),
        "metadata": metadata,
        "source_commit": SOURCE_COMMIT,
        "kernel_release": RELEASE,
        "config_delta": delta,
        "module_build_log_sha256": sha256_path(build_log_path),
        "module_symvers_sha256": sha256_path(symvers),
        "modules": module_records,
        "official_bluez_module_loader": {
            "source": (
                "https://gitlab.alpinelinux.org/alpine/aports/-/raw/master/"
                "main/bluez/modules-load.conf"
            ),
            "contents": ["uinput", "uhid"],
            "scope": (
                "The Alpine bluez package owns this file; the candidate does "
                "not duplicate it. bnep has the in-tree bt-proto-4 alias."
            ),
        },
        "service_files_present": False,
        "install_hooks_present": False,
        "modules_load_config_added": False,
        "device_installed": False,
        "modules_loaded": False,
        "hardware_pan_hid_verified": False,
    }
    manifest_path = args.output / "package-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    require(sha256_path(package) == manifest["sha256"], "package changed")
    print(json.dumps({
        "package": package.name,
        "sha256": manifest["sha256"],
        "bytes": manifest["bytes"],
        "modules": sorted(module_records),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
