#!/usr/bin/env python3
"""Independently verify the RMX1931 PM8150L flash-LED candidate pair."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tarfile
import tempfile

import libfdt


DTB_PATH = "/soc@0/spmi@c440000/pmic@5/led-controller@d300"
LED_PATH = DTB_PATH + "/led-0"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def run(argv: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv,
        capture_output=True,
        check=False,
    )


def string_list(value: bytes) -> list[str]:
    return [
        item.decode("utf-8", "replace")
        for item in value.rstrip(b"\0").split(b"\0")
        if item
    ]


def u32(value: bytes) -> int:
    if len(value) != 4:
        raise ValueError(f"expected one 32-bit cell, got {len(value)} bytes")
    return struct.unpack(">I", value)[0]


def u32_list(value: bytes) -> list[int]:
    if len(value) % 4:
        raise ValueError(f"expected 32-bit cells, got {len(value)} bytes")
    return list(struct.unpack(">" + "I" * (len(value) // 4), value))


def node_properties(fdt: libfdt.Fdt, path: str) -> dict[str, bytes]:
    offset = fdt.path_offset(path)
    properties = {}
    prop_offset = fdt.first_property_offset(
        offset, quiet=libfdt.QUIET_NOTFOUND)
    while prop_offset >= 0:
        prop = fdt.get_property_by_offset(prop_offset)
        properties[prop.name] = bytes(prop)
        prop_offset = fdt.next_property_offset(
            prop_offset, quiet=libfdt.QUIET_NOTFOUND)
    return properties


def node_exists(fdt: libfdt.Fdt, path: str) -> bool:
    try:
        fdt.path_offset(path)
        return True
    except libfdt.FdtException:
        return False


def check_dtb(base: Path, candidate: Path, checks: list[dict]) -> None:
    base_fdt = libfdt.Fdt(base.read_bytes())
    candidate_fdt = libfdt.Fdt(candidate.read_bytes())
    base_props = node_properties(base_fdt, DTB_PATH)
    candidate_props = node_properties(candidate_fdt, DTB_PATH)

    def check(name: str, condition: bool, detail: str) -> None:
        checks.append({
            "name": name,
            "passed": bool(condition),
            "detail": detail,
        })

    check(
        "baseline_flash_disabled",
        base_props.get("status") == b"disabled\0",
        repr(base_props.get("status")),
    )
    check(
        "candidate_flash_enabled",
        candidate_props.get("status") == b"okay\0",
        repr(candidate_props.get("status")),
    )
    check(
        "candidate_compatible",
        string_list(candidate_props.get("compatible", b"")) == [
            "qcom,pm8150l-flash-led",
            "qcom,spmi-flash-led",
        ],
        repr(string_list(candidate_props.get("compatible", b""))),
    )
    check(
        "candidate_reg",
        u32_list(candidate_props.get("reg", b"")) == [0xD300],
        repr(u32_list(candidate_props.get("reg", b""))),
    )
    check(
        "baseline_has_no_led_child",
        not node_exists(base_fdt, LED_PATH),
        LED_PATH,
    )
    check(
        "candidate_has_led_child",
        node_exists(candidate_fdt, LED_PATH),
        LED_PATH,
    )
    led = node_properties(candidate_fdt, LED_PATH)
    check(
        "led_function",
        led.get("function") == b"flash\0",
        repr(led.get("function")),
    )
    check("led_color_white", u32(led.get("color", b"")) == 0, "0")
    check(
        "led_sources_channels_1_2",
        u32_list(led.get("led-sources", b"")) == [1, 2],
        repr(u32_list(led.get("led-sources", b""))),
    )
    check(
        "led_torch_limit",
        u32(led.get("led-max-microamp", b"")) == 600000,
        "600000",
    )
    check(
        "flash_current_limit",
        u32(led.get("flash-max-microamp", b"")) == 2000000,
        "2000000",
    )
    check(
        "flash_timeout",
        u32(led.get("flash-max-timeout-us", b"")) == 1280000,
        "1280000",
    )


def check_semantic_diff(
    repo: Path,
    base: Path,
    candidate: Path,
    checks: list[dict],
) -> None:
    with tempfile.TemporaryDirectory(prefix="samurai-flash-diff-") as tmp:
        output = Path(tmp) / "diff.json"
        result = run([
            sys.executable,
            str(repo / "linux-port/scripts/diff-dtb.py"),
            str(base),
            str(candidate),
            "--output",
            str(output),
        ])
        if result.returncode != 0:
            checks.append({
                "name": "semantic_diff_generated",
                "passed": False,
                "detail": result.stderr.decode("utf-8", "replace"),
            })
            return
        diff = json.loads(output.read_text(encoding="utf-8"))
        checks.append({
            "name": "semantic_diff_generated",
            "passed": True,
            "detail": "semantic diff generated",
        })
        summary = diff.get("summary", {})
        exact = (
            summary.get("changed_property_count") == 1
            and summary.get("only_after_node_count") == 1
            and summary.get("only_before_node_count") == 0
            and summary.get("only_after_property_count") == 0
            and summary.get("only_before_property_count") == 0
            and summary.get("only_after_phandle_property_count") == 0
            and summary.get("only_before_phandle_property_count") == 0
        )
        checks.append({
            "name": "semantic_diff_is_only_flash_node_and_status",
            "passed": exact,
            "detail": json.dumps(summary, sort_keys=True),
        })
        changed = diff.get("changed_properties", [])
        checks.append({
            "name": "semantic_diff_changed_property_name",
            "passed": (
                len(changed) == 1
                and changed[0].get("path") == DTB_PATH
                and changed[0].get("property") == "status"
            ),
            "detail": json.dumps(changed, sort_keys=True),
        })
        added = diff.get("only_after_nodes", [])
        checks.append({
            "name": "semantic_diff_added_node_name",
            "passed": added == [LED_PATH],
            "detail": json.dumps(added, sort_keys=True),
        })


def check_json_report(
    path: Path,
    expected_sha256: str,
    checks: list[dict],
) -> dict:
    checks.append({
        "name": f"{path.name}_hash",
        "passed": sha256_file(path) == expected_sha256,
        "detail": sha256_file(path),
    })
    return json.loads(path.read_text(encoding="utf-8"))


def check_fat(
    image: Path,
    expected_image_sha256: str,
    expected_dtb_sha256: str,
    checks: list[dict],
) -> None:
    mtype = shutil.which("mtype")
    if mtype is None:
        checks.append({
            "name": "mtools_available",
            "passed": False,
            "detail": "mtype not found; run this verifier in the WSL build host",
        })
        return
    checks.append({
        "name": "mtools_available",
        "passed": True,
        "detail": mtype,
    })
    for name, expected in (
        ("Image", expected_image_sha256),
        ("samurai.dtb", expected_dtb_sha256),
    ):
        result = run([mtype, "-i", str(image), f"::/{name}"])
        actual = sha256_bytes(result.stdout) if result.returncode == 0 else ""
        checks.append({
            "name": f"fat_{name}_hash",
            "passed": result.returncode == 0 and actual == expected,
            "detail": actual,
        })
    fsck = shutil.which("fsck.vfat")
    if fsck is None:
        checks.append({
            "name": "fat_fsck_available",
            "passed": False,
            "detail": "fsck.vfat not found",
        })
    else:
        result = run([fsck, "-n", str(image)])
        checks.append({
            "name": "fat_fsck_clean",
            "passed": result.returncode == 0,
            "detail": result.stdout.decode("utf-8", "replace").strip(),
        })


def check_module(
    archive: Path,
    expected_sha256: str,
    checks: list[dict],
) -> None:
    with tarfile.open(archive, "r:gz") as tar:
        matches = [
            member for member in tar.getmembers()
            if member.isfile() and member.name.endswith(
                "/drivers/leds/flash/leds-qcom-flash.ko")
        ]
        if len(matches) != 1:
            checks.append({
                "name": "flash_module_member",
                "passed": False,
                "detail": [member.name for member in matches],
            })
            return
        member = matches[0]
        handle = tar.extractfile(member)
        if handle is None:
            raise RuntimeError("cannot read flash module from archive")
        actual = sha256_bytes(handle.read())
        checks.append({
            "name": "flash_module_member",
            "passed": actual == expected_sha256,
            "detail": f"{member.name} {actual}",
        })


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
            "flash-led-candidate-20261109"
        ),
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    repo = args.repo.resolve()
    candidate_dir = args.candidate_dir.resolve()

    paths = {
        "baseline_dtb": candidate_dir / "baseline.dtb",
        "candidate_dtb": candidate_dir / "sm8150-samurai-v731-flash-led.dtb",
        "candidate_dts": candidate_dir / "sm8150-samurai-flash-led-candidate.dts",
        "boot": candidate_dir / "boot-build-2/boot-eud-production-off.img",
        "kernel_fat": candidate_dir / "recovery-kernel-fat-flash-led.img",
        "boot_result": candidate_dir / "boot-build-2/result.json",
        "metadata_review": candidate_dir / "metadata-review.json",
        "contract_report": candidate_dir / "dtb-contract-offline.json",
        "self_test": candidate_dir / "dtb-contract-self-test.json",
        "rollback_boot": candidate_dir / "rollback/boot-baseline-9b9be136.img",
        "rollback_fat": candidate_dir / "rollback/recovery-kernel-fat-baseline.img",
        "modules": (
            Path("/mnt/e/edk2-samurai-out/standard-arm64-v731")
            / "camera-final-boot/modules-v731-camera.tar.gz"
        ),
        "source_lock": repo / "linux-port/dts/v731/source-lock.json",
    }
    expected = {
        "baseline_dtb": "3799ec6c7d3e0c67a657859a37b2fe147fa21a9dedc84d49c8eb83fd8debc805",
        "candidate_dtb": "c585ffdf0fd3714524bfad3c0b7005f40803816e31f50cbd8398a4979a2edbbd",
        "candidate_dts": "dcc6fe191071915d139c8e53f820f335f96726295aa06009890b5e575b35b270",
        "boot": "9196b22ce55bf7459c95576c85e33280bd9b1452f983dac20dbefd6047a541f0",
        "kernel_fat": "74804f420a4969da99e123ec6eb48c7834e7c074fbb0609bb52aa5dca2750cd2",
        "boot_result": "96538f6c3b3c9a4eb553ccaf70d7e4d5659e81d92d6180d3b4bbf93af6cb40ec",
        "metadata_review": "72ef2d31782710b9ef541585204361ca8d4e978e17116ac347f6633086891fb5",
        "contract_report": "a29c62d14ca96f89956575c14fe5feebb6470abe9b69f662c31a941e530a6e8c",
        "self_test": "79cb5436708fd74b75c3002708d81bb6dc4bd4103e9e503e9f7a419f150e1cf3",
        "rollback_boot": "9b9be136bd3ee2328f0c4273a829471ad0cd73a7fe7d718825ac024f7af3ae54",
        "rollback_fat": "6a6aa520e4adda750450c3fd9b80a553c1988d6d76803c674c279b3a5df4f562",
    }
    checks: list[dict] = []
    for name, path in paths.items():
        if not path.is_file():
            checks.append({
                "name": f"{name}_exists",
                "passed": False,
                "detail": str(path),
            })
        else:
            checks.append({
                "name": f"{name}_exists",
                "passed": True,
                "detail": str(path),
            })
    if not all(item["passed"] for item in checks):
        report = {
            "schema": "samurai-flash-led-candidate-verifier-v1",
            "passed": False,
            "candidate_dir": str(candidate_dir),
            "checks": checks,
        }
        print(json.dumps(report, indent=2, sort_keys=True))
        return 1

    for name in (
        "baseline_dtb", "candidate_dtb", "candidate_dts", "boot",
        "kernel_fat", "rollback_boot", "rollback_fat",
    ):
        actual = sha256_file(paths[name])
        checks.append({
            "name": f"{name}_hash",
            "passed": actual == expected[name],
            "detail": actual,
        })

    boot_result = check_json_report(
        paths["boot_result"], expected["boot_result"], checks)
    metadata = check_json_report(
        paths["metadata_review"], expected["metadata_review"], checks)
    self_test = check_json_report(
        paths["self_test"], expected["self_test"], checks)
    contract = check_json_report(
        paths["contract_report"], expected["contract_report"], checks)

    checks.append({
        "name": "boot_result_scope",
        "passed": (
            boot_result.get("source_boot_sha256") == expected["rollback_boot"]
            and boot_result.get("dtb_sha256") == expected["candidate_dtb"]
            and boot_result.get("boot_sha256") == expected["boot"]
            and boot_result.get("changed_main_ffs") == [
                "25462cda-221f-47df-ac1d-259cfaa4e326"
            ]
            and boot_result.get("unchanged_main_ffs") == 100
        ),
        "detail": "source boot, DTB, boot and changed-FFS set",
    })
    checks.append({
        "name": "metadata_review_scope",
        "passed": (
            metadata.get("passed") is True
            and metadata.get("classification") == "printable_metadata_only"
            and metadata.get("candidate_boot_sha256") == expected["boot"]
            and all(
                item.get("classification") == "identical"
                for item in metadata.get("metadata_modules", {}).values()
            )
        ),
        "detail": "BdsDxe/PlatformSmbiosDxe/UiApp identical",
    })
    checks.append({
        "name": "dtb_contract_scope",
        "passed": (
            contract.get("passed") is True
            and contract.get("summary", {}).get("resources_checked") == 23
            and contract.get("summary", {}).get("failures") == 0
        ),
        "detail": "23 resources, no failures",
    })
    checks.append({
        "name": "dtb_self_test_scope",
        "passed": (
            self_test.get("passed") is True
            and any(
                case.get("id") == "flash_led_additive_accepted"
                and case.get("actual_passed") is True
                for case in self_test.get("cases", [])
            )
        ),
        "detail": "flash additive case accepted",
    })

    check_dtb(paths["baseline_dtb"], paths["candidate_dtb"], checks)
    check_semantic_diff(
        repo, paths["baseline_dtb"], paths["candidate_dtb"], checks)
    check_fat(
        paths["kernel_fat"],
        "aa6c4b6b43ec45f4c41d3d420b980e35876860537cb6f2cb96ec5063aab8432a",
        expected["candidate_dtb"],
        checks,
    )
    check_module(
        paths["modules"],
        "b90a9b19ca3e13bc4ed879134ffa9aba81659a42faa89e02447630a5edd354a7",
        checks,
    )

    source_lock = json.loads(paths["source_lock"].read_text(encoding="utf-8"))
    flash = source_lock.get("flash_led_candidate", {})
    checks.append({
        "name": "source_lock_candidate",
        "passed": (
            source_lock.get("status", "").startswith("flash_led_candidate_")
            and flash.get("boot_candidate", {}).get("sha256") == expected["boot"]
            and flash.get("kernel_fat", {}).get("sha256") == expected["kernel_fat"]
            and flash.get("dts", {}).get("dtb_sha256") == expected["candidate_dtb"]
        ),
        "detail": "source-lock candidate hashes",
    })
    checks.append({
        "name": "source_dts_wrapper",
        "passed": (
            flash.get("dts", {}).get("candidate_source_sha256")
            == expected["candidate_dts"]
        ),
        "detail": "candidate DTS source hash",
    })
    budget = flash.get("hardware_identification", {}).get(
        "current_budget", {})
    checks.append({
        "name": "source_lock_flash_budget",
        "passed": (
            budget.get("vendor_flash_each_default_ua") == 1000000
            and budget.get("vendor_flash_each_max_ua") == 1500000
            and budget.get("vendor_torch_each_default_ua") == 300000
            and budget.get("vendor_torch_each_max_ua") == 500000
            and budget.get("logical_dual_channel_flash_default_ua") == 2000000
            and budget.get("logical_dual_channel_torch_default_ua") == 600000
            and budget.get("mainline_flash_total_clamp_ua") == 2000000
            and budget.get("mainline_torch_per_channel_clamp_ua") == 500000
            and budget.get("mainline_timeout_clamp_us") == 1280000
            and budget.get("candidate_within_vendor_and_mainline_limits") is True
        ),
        "detail": "candidate 600 mA torch and 2 A flash stay within vendor defaults and mainline clamps",
    })
    for name, section_name in (
        ("flasher", "flasher"),
        ("runtime_probe", "runtime_probe"),
    ):
        section = flash.get(section_name, {})
        helper = repo / section.get("repo_path", "")
        helper_exists = helper.is_file()
        helper_hash = sha256_file(helper) if helper_exists else ""
        checks.append({
            "name": f"source_lock_{name}_helper",
            "passed": (
                helper_exists
                and section.get("bytes") == helper.stat().st_size
                and section.get("sha256") == helper_hash
            ),
            "detail": f"{helper} {helper_hash}",
        })
    verifier_section = flash.get("offline_verifier", {})
    verifier_path = Path(__file__).resolve()
    verifier_hash = sha256_file(verifier_path)
    checks.append({
        "name": "source_lock_verifier_self",
        "passed": (
            verifier_section.get("repo_path")
            == "linux-port/scripts/verify-flash-led-candidate.py"
            and verifier_section.get("bytes") == verifier_path.stat().st_size
            and verifier_section.get("sha256") == verifier_hash
        ),
        "detail": f"{verifier_path} {verifier_hash}",
    })

    report = {
        "schema": "samurai-flash-led-candidate-verifier-v1",
        "passed": all(item["passed"] for item in checks),
        "candidate_dir": str(candidate_dir),
        "checks": checks,
        "scope": (
            "Offline independent candidate verification. It proves artifact "
            "identity, DTB semantics, boot/FAT contents and source-lock "
            "consistency; it does not prove device boot or LED operation."
        ),
    }
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    sys.stdout.write(text)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
