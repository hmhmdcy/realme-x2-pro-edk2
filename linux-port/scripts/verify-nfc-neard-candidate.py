#!/usr/bin/env python3
"""Verify the offline samurai-platform 5-r22 neard integration candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


EXPECTED = {
    "package": "bc3f6d59d1aaf5ae800bc512205b1cbd5da71a3412a64ac651396a4d8ba82f51",
    "index": "273e3992322030d9e006a235778d4831bd8262044d7110ad8d68680410c05a8b",
    "manifest": "7337df035195c61058d9c0528301f53356de0db01bdcfd30271c51af112d761a",
    "signer_pub": "dbfa32c3c97d5624e558547ec6e47725f77a1f4f0569455288f79ca66269bbc3",
    "apkbuild": "47be866ee395d032331073338e0e6fe6eabf6b97de8bcda4f7ac31fbb7cb6b8d",
    "post_install": "79b969cc0d41c5916a0c6429cf387620ff5ff9e50196fce6533848d03ca276d1",
    "probe": "1ff161c39b96141f486b59dbefa985fa4b35d6b699841d3b6ffb9198dd8ba6f1",
    "doc": "206bb2ff6e8a6edadc19e3b426099e3fdbdd48fcd025b55cdd89167083f98234",
    "neard": "027df5f8637a1fd50f34abba456b9c96ec838af53d4f09cb8d7bf16168487069",
    "build_script": "a070717880ea631212d4a1023363dfdFB473bc7e00abed531b21d90ee503a534".lower(),
    "aports_commit": "bd6dd5c256ded7726539c28a7dcd984237d82006",
    "neard_apkbuild": "bd8c77a5bd87d6b1ec5addf79516ecb9cf08f6e09e5d5082827a6c4e2f9614af",
    "neard_initd": "efee90c44b86fe93a25efb4a978cc71faba858d11fd340a83a03b57d64ed2755",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def add(checks: list[dict], name: str, passed: bool, detail: str) -> None:
    checks.append({"name": name, "passed": bool(passed), "detail": detail})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path(__file__).resolve().parents[2],
    )
    parser.add_argument(
        "--candidate-dir",
        type=Path,
        default=Path(
            "/mnt/e/edk2-samurai-out/standard-arm64-v731/"
            "nfc-neard-20261109"
        ),
    )
    parser.add_argument("--apk", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    repo = args.repo.resolve()
    candidate = args.candidate_dir.resolve()
    output = args.output or candidate / "verification.json"
    checks: list[dict] = []

    package = candidate / "samurai-platform-5-r22.apk"
    index = candidate / "packages.adb"
    manifest_path = candidate / "package-manifest.json"
    signer_pub = candidate / "samurai-linux-203.rsa.pub"
    neard_apk = candidate / "neard-0.20-r0.apk"
    result_path = candidate / "result.json"
    for name, path, expected in (
        ("package", package, EXPECTED["package"]),
        ("index", index, EXPECTED["index"]),
        ("manifest", manifest_path, EXPECTED["manifest"]),
        ("signer_pub", signer_pub, EXPECTED["signer_pub"]),
        ("neard_apk", neard_apk, EXPECTED["neard"]),
    ):
        exists = path.is_file()
        add(checks, f"{name}_exists", exists, str(path))
        if exists:
            actual = sha256(path)
            add(checks, f"{name}_sha256", actual == expected, actual)
    add(checks, "result_exists", result_path.is_file(), str(result_path))

    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        packages = manifest.get("packages", [])
        platform = [
            item for item in packages
            if item.get("name") == "samurai-platform"
            and item.get("version") == "5-r22"
        ]
        add(
            checks,
            "manifest_platform_5_r22",
            len(platform) == 1,
            str(len(platform)),
        )
        if len(platform) == 1:
            depends = platform[0].get("metadata", {}).get("depends", "")
            add(
                checks,
                "manifest_neard_openrc",
                "neard-openrc" in depends.split(),
                depends,
            )
            add(
                checks,
                "manifest_arch_noarch",
                platform[0].get("arch") == "noarch",
                str(platform[0].get("arch")),
            )

    source_inputs = {
        "apkbuild": repo / "linux-port/packages/samurai-platform/APKBUILD",
        "post_install": repo / "linux-port/packages/samurai-platform/samurai-platform.post-install",
        "probe": repo / "linux-port/scripts/test-nfc-neard.py",
        "doc": repo / "linux-port/docs/NFC-NEARD.md",
        "build_script": repo / "linux-port/scripts/build-board-packages.py",
    }
    for name, path in source_inputs.items():
        exists = path.is_file()
        add(checks, f"{name}_exists", exists, str(path))
        if exists:
            actual = sha256(path)
            add(
                checks,
                f"{name}_sha256",
                actual == EXPECTED[name],
                actual,
            )

    post_install = source_inputs["post_install"]
    if post_install.is_file():
        text = post_install.read_text(encoding="utf-8")
        add(
            checks,
            "post_install_adds_neard_default",
            "rc-update add neard default" in text,
            "default runlevel",
        )
        add(
            checks,
            "post_install_does_not_start_live_daemon",
            "rc-service neard start" not in text
            and "rc-service neard restart" not in text,
            "no live daemon start/restart",
        )

    if result_path.is_file():
        result = json.loads(result_path.read_text(encoding="utf-8"))
        source = result.get("official_source", {})
        add(
            checks,
            "aports_commit",
            source.get("aports_commit") == EXPECTED["aports_commit"],
            str(source.get("aports_commit")),
        )
        add(
            checks,
            "neard_apkbuild_sha256",
            source.get("apkbuild_sha256") == EXPECTED["neard_apkbuild"],
            str(source.get("apkbuild_sha256")),
        )
        add(
            checks,
            "neard_initd_sha256",
            source.get("initd_sha256") == EXPECTED["neard_initd"],
            str(source.get("initd_sha256")),
        )
        add(
            checks,
            "private_driver_absent",
            result.get("transaction", {}).get("private_driver") is False,
            "transaction.private_driver=false",
        )
        add(
            checks,
            "private_ioctl_absent",
            result.get("transaction", {}).get("private_ioctl") is None
            or result.get("transaction", {}).get("private_ioctl") is False,
            str(result.get("transaction", {}).get("private_ioctl")),
        )

    if args.apk:
        add(
            checks,
            "apk_tool_exists",
            args.apk.is_file(),
            str(args.apk),
        )
        if args.apk.is_file() and package.is_file():
            verify = subprocess.run(
                [
                    str(args.apk),
                    "--keys-dir",
                    str(candidate),
                    "verify",
                    str(package),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            add(
                checks,
                "package_signature",
                verify.returncode == 0,
                (verify.stdout + verify.stderr).strip(),
            )

    passed = bool(checks) and all(item["passed"] for item in checks)
    report = {
        "schema": "samurai-nfc-neard-candidate-verifier-v1",
        "passed": passed,
        "candidate_dir": str(candidate),
        "checks": checks,
        "failures": [item for item in checks if not item["passed"]],
        "scope": (
            "Offline package/hash/dependency and source-boundary checks only. "
            "It does not install the package, start neard, probe nfc0 or read "
            "a physical NFC tag."
        ),
    }
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
