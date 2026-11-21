#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path


HERE = Path(__file__).resolve().parent
BUILD_ROOT = Path(
    "/home/cy122/charging-management-20261023/charging-integration-20261026-01/build"
)
MODULE_ROOT = Path("/home/cy122/charging-management-20261023/usb-input-irq-wake-r8-module-01")
MODULE = MODULE_ROOT / "module/samurai-usb-input.ko"
EXPORT = Path(
    "/mnt/e/edk2-samurai-out/charging-management-20261023/"
    "usb-input-irq-wake-r8-module-private-01"
)
EXPORTED = EXPORT / "samurai-usb-input-irq-wake-r8-private.ko"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def output(argv: list[str]) -> str:
    return subprocess.check_output(argv, text=True).strip()


def main() -> None:
    assert MODULE.is_file()
    assert sha(MODULE) == sha(EXPORTED)
    assert (HERE / "test-result.json").is_file()
    tests = json.loads((HERE / "test-result.json").read_text())
    assert tests["passed"] and tests["groups"] == 10

    log = (MODULE_ROOT / "build.log").read_text(errors="replace")
    diagnostics = [
        line
        for line in log.splitlines()
        if re.search(r"\b(?:warning|error):|undefined!", line, re.I)
    ]
    assert not diagnostics, diagnostics

    exports = {}
    for line in (BUILD_ROOT / "vmlinux.symvers").read_text().splitlines():
        row = line.split()
        assert len(row) >= 3 and row[2] == "vmlinux"
        exports[row[1]] = row[0]
    imports = []
    for line in output(["aarch64-linux-gnu-nm", "-u", str(MODULE)]).splitlines():
        row = line.split()
        assert len(row) == 2 and row[0] == "U"
        imports.append(row[1])
    unresolved = sorted(set(imports) - exports.keys())
    assert not unresolved, unresolved

    release = (BUILD_ROOT / "include/config/kernel.release").read_text().strip()
    assert release == "7.3.0-rc6-rmx1931-samurai-k363+"
    vermagic = output(["modinfo", "-F", "vermagic", str(MODULE)])
    assert vermagic == (
        "7.3.0-rc6-rmx1931-samurai-k363+ SMP preempt mod_unload aarch64"
    )
    intree = output(["modinfo", "-F", "intree", str(MODULE)]) or "N"
    assert intree == "N"
    assert output(["modinfo", "-F", "name", str(MODULE)]) == "samurai_usb_input"
    assert output(["modinfo", "-F", "depends", str(MODULE)]) == ""
    assert "AArch64" in subprocess.check_output(
        ["aarch64-linux-gnu-readelf", "-h", str(MODULE)], text=True
    )

    result = {
        "schema": 1,
        "passed": True,
        "source_sha256": sha(HERE / "source/samurai-usb-input.c"),
        "decoder_sha256": sha(HERE / "source/samurai-usb-input-decode.h"),
        "module_sha256": sha(MODULE),
        "module_bytes": MODULE.stat().st_size,
        "module_path": str(MODULE),
        "exported_private_module_path": str(EXPORTED),
        "release": release,
        "vermagic": vermagic,
        "intree": intree,
        "ELF_machine": "AArch64",
        "strong_import_count": len(set(imports)),
        "unresolved_strong_imports": unresolved,
        "Image_vmlinux_symvers_sha256": sha(BUILD_ROOT / "vmlinux.symvers"),
        "build_log_sha256": sha(MODULE_ROOT / "build.log"),
        "diagnostics": [],
        "unit_test_result": tests,
        "module_only_no_Image_link": True,
        "phone_or_fastboot_accessed": False,
        "physical_usb_wakeup_accepted": False,
    }
    raw = json.dumps(result, indent=2, sort_keys=True) + "\n"
    (HERE / "build-result.json").write_text(raw)
    (EXPORT / "build-result.json").write_text(raw)
    (EXPORT / "test-result.json").write_text(
        json.dumps(tests, indent=2, sort_keys=True) + "\n"
    )
    print(raw, end="")


if __name__ == "__main__":
    main()
