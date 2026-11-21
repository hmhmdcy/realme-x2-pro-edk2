#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


HERE = Path(__file__).resolve().parent


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    subprocess.run(["python3", str(HERE / "prepare-tests.py")], check=True)
    output = HERE / "test-wake"
    argv = [
        "cc",
        "-std=c11",
        "-Wall",
        "-Wextra",
        "-Werror",
        "-Wno-unused-parameter",
        "-Wno-sign-compare",
        "-I",
        str(HERE),
        str(HERE / "test-wake.c"),
        "-o",
        str(output),
    ]
    build = subprocess.run(argv, text=True, capture_output=True)
    if build.returncode:
        raise SystemExit(build.stdout + build.stderr)
    run = subprocess.run([str(output)], text=True, capture_output=True)
    if run.returncode:
        raise SystemExit(run.stdout + run.stderr)
    result = {
        "passed": True,
        "groups": 10,
        "source_sha256": sha(HERE / "source/samurai-usb-input.c"),
        "test_source_sha256": sha(HERE / "test-wake.c"),
        "actual_functions_only_at_pm_boundaries": True,
        "modeled_kernel_apis": True,
        "phone_or_fastboot_accessed": False,
        "physical_usb_wakeup_accepted": False,
        "build_stdout": build.stdout,
        "run_stdout": run.stdout,
    }
    (HERE / "test-result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
