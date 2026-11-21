from __future__ import annotations

import ctypes
import errno
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


TRIAL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TRIAL_DIR))

import acknowledge_trial  # noqa: E402
import postboot_audit  # noqa: E402
import trial_autoaudit  # noqa: E402
import trial_common  # noqa: E402
import trial_guard  # noqa: E402
import trial_stage  # noqa: E402


SMALL_BYTES = {"boot": 96, "logdump": 64}
OLD_BOOT_ID = "11111111-1111-1111-1111-111111111111"
NEW_BOOT_ID = "22222222-2222-2222-2222-222222222222"
OTHER_BOOT_ID = "33333333-3333-3333-3333-333333333333"
OLD_VERSION = "#508 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026"
SERIAL = "62bc28a1"


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path: Path, data: str | bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = data.encode() if isinstance(data, str) else data
    path.write_bytes(raw)
    return path


def runlevel_current_record(fixture: dict) -> dict:
    state = fixture["runlevel_state"]
    if state.get("inspect_error"):
        raise trial_common.TrialError(state["inspect_error"])
    if state["present"]:
        return {
            "target": trial_common.RUNLEVEL_PATH.as_posix(),
            "before": "enabled",
            "added": False,
            "link_target": state["link_target"],
            "verified": True,
        }
    return {
        "target": trial_common.RUNLEVEL_PATH.as_posix(),
        "before": "missing",
        "added": False,
        "link_target": None,
        "verified": True,
    }


def runlevel_kwargs(fixture: dict) -> dict:
    state = fixture["runlevel_state"]

    def inspector(_runtime):
        return runlevel_current_record(fixture)

    def enabler(_runtime, record):
        current = runlevel_current_record(fixture)
        if current["before"] != record["before"]:
            raise trial_common.TrialError("runlevel state changed in test")
        if record["before"] == "enabled":
            return dict(record)
        state["enable_calls"] = state.get("enable_calls", 0) + 1
        state["present"] = True
        state["link_target"] = trial_common.SERVICE_PATH.as_posix()
        return {
            **record,
            "before": "missing",
            "added": True,
            "link_target": state["link_target"],
            "verified": True,
        }

    def restorer(_runtime, record):
        state["restore_calls"] = state.get("restore_calls", 0) + 1
        current = runlevel_current_record(fixture)
        if record["added"]:
            if current["before"] != "enabled":
                raise trial_common.TrialError("test runlevel link is missing")
            state["present"] = False
            state["link_target"] = None
            return {**record, "removed": True, "verified": True}
        if current["before"] != record["before"]:
            raise trial_common.TrialError("test runlevel state changed")
        return {**record, "removed": False, "verified": True}

    return {
        "runlevel_inspector": inspector,
        "runlevel_enabler": enabler,
        "runlevel_restorer": restorer,
    }


def blob(label: str, size: int) -> bytes:
    seed = hashlib.sha256(label.encode()).digest()
    return (seed * ((size + len(seed) - 1) // len(seed)))[:size]


def snapshot(root: Path) -> dict[str, str]:
    result = {}
    for path in sorted(Path(root).rglob("*")):
        if path.is_file():
            result[str(path.relative_to(root))] = sha(path)
    return result


def build_manifest(
    package: Path,
    old_paths: dict[str, Path],
    new_paths: dict[str, Path],
    old_module: Path,
    new_module: Path,
    dtb_path: Path,
    boot_receipt_path: Path,
    main_manifest_path: Path,
) -> dict:
    device_files = {
        str(target): {
            "source": source,
            "target": str(target),
            "mode": mode,
            "sha256": sha(package / source),
        }
        for target, (source, mode) in trial_common.DEVICE_FILE_SPECS.items()
    }
    carriers = {}
    for name in SMALL_BYTES:
        carriers[name] = {
            "bytes": SMALL_BYTES[name],
            "old": sha(old_paths[name]),
            "new": sha(new_paths[name]),
            "old_path": str(old_paths[name]),
            "new_path": str(new_paths[name]),
        }
    return {
        "schema": 1,
        "trial_id": trial_common.TRIAL_ID,
        "kernel_version": trial_common.VERSION,
        "release": trial_common.RELEASE,
        "watch_seconds": trial_common.WATCH_SECONDS,
        "token": trial_common.TOKEN,
        "accepted_token_scope": "boot_id",
        "high_voltage_permitted": False,
        "baseline_tainted": trial_common.EXPECTED_TAINTED,
        "fastboot": {
            "serial": SERIAL,
            "product": "msmnile",
            "path": r"C:\Users\cy122\Downloads\platform-tools\platform-tools\fastboot.exe",
            "host_fetch_unavailable": False,
            "guard_carrier_readback_required": True,
        },
        "device_files": device_files,
        "kernel_module": {
            "name": trial_common.MODULE_NAME,
            "source": trial_common.MODULE_SOURCE,
            "target": trial_common.MODULE_PATH.as_posix(),
            "mode": trial_common.MODULE_MODE,
            "old_sha256": sha(old_module),
            "old_bytes": old_module.stat().st_size,
            "new_sha256": sha(new_module),
            "new_bytes": new_module.stat().st_size,
        },
        "main_manifest": {
            "target": trial_common.MAIN_MANIFEST_PATH.as_posix(),
            "old_sha256": sha(main_manifest_path),
            "service_target": trial_common.SERVICE_PATH.as_posix(),
        },
        "carriers": carriers,
        "dtb": {
            "path": str(dtb_path),
            "sha256": sha(dtb_path),
            "bytes": dtb_path.stat().st_size,
            "embedded_in_boot": True,
        },
        "boot_receipt": {
            "path": str(boot_receipt_path),
            "sha256": sha(boot_receipt_path),
            "bytes": boot_receipt_path.stat().st_size,
            "boot_path_suffix": new_paths["boot"].as_posix(),
            "dtb_path_suffix": dtb_path.as_posix(),
        },
    }


def package_copy(destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copy2(TRIAL_DIR / "trial_common.py", destination / "trial_common.py")
    shutil.copy2(TRIAL_DIR / "trial_guard.py", destination / "trial_guard.py")
    shutil.copy2(TRIAL_DIR / "postboot_audit.py", destination / "postboot_audit.py")
    shutil.copy2(
        TRIAL_DIR / "trial_autoaudit.py",
        destination / "trial_autoaudit.py",
    )
    (destination / "service").mkdir(exist_ok=True)
    shutil.copy2(
        TRIAL_DIR / "service/samurai-charging",
        destination / "service/samurai-charging",
    )
    (destination / "modules").mkdir(exist_ok=True)
    (destination / "trial_common.py").chmod(0o644)
    (destination / "trial_guard.py").chmod(0o755)
    (destination / "postboot_audit.py").chmod(0o644)
    (destination / "trial_autoaudit.py").chmod(0o755)
    (destination / "service/samurai-charging").chmod(0o755)
    return destination


def make_fixture(base: Path) -> dict:
    base = Path(base)
    package = package_copy(base / "package")
    old_paths = {
        "boot": write(base / "images/old-boot.img", blob("old-boot", SMALL_BYTES["boot"])),
        "logdump": write(
            base / "images/old-logdump.img", blob("old-logdump", SMALL_BYTES["logdump"])
        ),
    }
    new_paths = {
        "boot": write(base / "images/new-boot.img", blob("new-boot", SMALL_BYTES["boot"])),
        "logdump": write(
            base / "images/new-logdump.img", blob("new-logdump", SMALL_BYTES["logdump"])
        ),
    }
    proc = base / "proc"
    write(proc / "version", OLD_VERSION)
    write(proc / "sys/kernel/random/boot_id", OLD_BOOT_ID + "\n")
    target = base / "target"
    original_service = write(
        target / "etc/init.d/samurai-charging",
        "#!/sbin/openrc-run\n# original service\n",
    )
    original_service.chmod(0o755)
    old_module = write(
        target / Path(str(trial_common.MODULE_PATH)).relative_to("/"),
        blob("old-module", 128),
    )
    old_module.chmod(0o644)
    new_module = write(
        package / trial_common.MODULE_SOURCE,
        blob("new-module", 192),
    )
    new_module.chmod(0o644)
    main_manifest = write(
        target / "usr/share/samurai-charging/manifest.json",
        json.dumps(
            {
                "release": trial_common.RELEASE,
                "modules": {
                    trial_common.MODULE_NAME: {
                        "target": trial_common.MODULE_PATH.as_posix(),
                        "sha256": sha(old_module),
                    },
                },
                "installed_files": {
                    trial_common.SERVICE_PATH.as_posix(): sha(original_service),
                    trial_common.MODULE_PATH.as_posix(): sha(old_module),
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )
    devices = {
        "boot": write(base / "devices/boot.img", old_paths["boot"].read_bytes()),
        "logdump": write(base / "devices/logdump.img", old_paths["logdump"].read_bytes()),
    }
    dtb_path = write(base / "images/new.dtb", blob("new-dtb", 160))
    boot_receipt_path = write(
        base / "images/boot-receipt.json",
        json.dumps(
            {
                "passed": True,
                "boot_path": str(new_paths["boot"]),
                "boot_sha256": sha(new_paths["boot"]),
                "native_DTB_sha256": sha(dtb_path),
                "parent_inputs_before": {str(dtb_path): sha(dtb_path)},
                "parent_inputs_after": {str(dtb_path): sha(dtb_path)},
            }
        )
        + "\n",
    )
    manifest = build_manifest(
        package,
        old_paths,
        new_paths,
        old_module,
        new_module,
        dtb_path,
        boot_receipt_path,
        main_manifest,
    )
    manifest_path = write(
        package / "manifest.json",
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
    )
    identities = {
        "boot": {"partuuid": "boot-partuuid", "start": 10, "sectors": 8, "partition": 3},
        "logdump": {
            "partuuid": "log-partuuid",
            "start": 20,
            "sectors": 8,
            "partition": 7,
        },
    }
    return {
        "base": base,
        "package": package,
        "manifest": manifest,
        "manifest_path": manifest_path,
        "old_paths": old_paths,
        "new_paths": new_paths,
        "proc": proc,
        "target": target,
        "target_manifest": target
        / Path(str(trial_common.MANIFEST_PATH)).relative_to("/"),
        "main_manifest": main_manifest,
        "original_main_manifest_sha256": sha(main_manifest),
        "original_main_manifest_bytes": main_manifest.read_bytes(),
        "devices": devices,
        "identities": identities,
        "dtb_path": dtb_path,
        "boot_receipt_path": boot_receipt_path,
        "root": base / "evidence",
        "original_service": original_service,
        "original_service_bytes": original_service.read_bytes(),
        "original_service_sha256": sha(original_service),
        "old_module": old_module,
        "new_module": new_module,
        "original_module_bytes": old_module.read_bytes(),
        "original_module_sha256": sha(old_module),
        "new_module_sha256": sha(new_module),
        "runlevel_state": {
            "present": False,
            "link_target": None,
            "enable_calls": 0,
            "restore_calls": 0,
        },
    }


def make_stage_runtime(
    fixture: dict,
    *,
    restarter=None,
    stopper=None,
    syncer=None,
    fsyncer=None,
) -> trial_stage.StageRuntime:
    return trial_stage.StageRuntime(
        package=fixture["package"],
        root=fixture["root"],
        proc_root=fixture["proc"],
        target_root=fixture["target"],
        manifest_path=fixture["manifest_path"],
        devices=fixture["devices"],
        identities=fixture["identities"],
        require_root=False,
        strict_carrier_pins=False,
        partition_bytes=SMALL_BYTES,
        serial_reader=lambda: "",
        service_stopper=stopper
        or (lambda: {"returncode": 0, "stdout": {"managed": False}}),
        syncer=syncer or (lambda: None),
        fsyncer=fsyncer or (lambda paths: None),
        bootloader_restarter=restarter or (lambda: None),
        **runlevel_kwargs(fixture),
    )


def stage_fixture(fixture: dict, *, reboot_calls: list | None = None) -> dict:
    calls = reboot_calls if reboot_calls is not None else []
    runtime = make_stage_runtime(
        fixture,
        restarter=lambda: calls.append("restart2"),
    )
    receipt = trial_stage.stage(runtime, execute=True, operator_serial=SERIAL)
    fixture["runtime"] = runtime
    fixture["receipt"] = receipt
    fixture["stage_reboot_calls"] = calls
    return fixture


def new_boot(fixture: dict) -> None:
    write(fixture["proc"] / "version", trial_common.VERSION + "\n")
    write(fixture["proc"] / "sys/kernel/random/boot_id", NEW_BOOT_ID + "\n")
    for name in SMALL_BYTES:
        fixture["devices"][name].write_bytes(fixture["new_paths"][name].read_bytes())


def guard_runtime(
    fixture: dict,
    *,
    boottime_value: float = 100.0,
    reboot_calls: list | None = None,
) -> trial_guard.Runtime:
    calls = reboot_calls if reboot_calls is not None else []
    return trial_guard.Runtime(
        root=fixture["root"],
        proc_root=fixture["proc"],
        target_root=fixture["target"],
        manifest_path=fixture["target_manifest"],
        devices=fixture["devices"],
        identities=fixture["identities"],
        require_root=False,
        strict_carrier_pins=False,
        partition_bytes=SMALL_BYTES,
        boottime=lambda: boottime_value,
        sleep=lambda _: None,
        reboot=lambda: calls.append("reboot"),
        runlevel_restorer=runlevel_kwargs(fixture)["runlevel_restorer"],
    )


def write_watchdog_state(fixture: dict, *, boot_id: str = NEW_BOOT_ID) -> None:
    write(
        fixture["root"] / "state.json",
        json.dumps(
            {
                "event": "watchdog-running",
                "boot_id": boot_id,
                "boottime": 10.0,
                "deadline_boottime": 310.0,
                "pid": 4242,
            }
        )
        + "\n",
    )
    write(
        fixture["proc"] / "4242/cmdline",
        b"python3\0-B\0/usr/lib/samurai-charging/trial_guard.py\0watch\0"
        b"--deadline-boottime\000310.0\0",
    )
    write(
        fixture["proc"] / "4242/stat",
        "4242 (python3) S 1 4242 4242 0 -1 4194560 0 0 0 0 0 0 0 0 20 0 1 0 1 0 0\n",
    )


def complete_report(fixture: dict, *, boot_id: str = NEW_BOOT_ID) -> dict:
    return {
        "schema": 1,
        "trial_id": trial_common.TRIAL_ID,
        "passed": True,
        "read_only": True,
        "accepted_token_written": False,
        "high_voltage_accessed": False,
        "boot_id": boot_id,
        "version": trial_common.VERSION,
        "manifest_sha256": sha(fixture["target_manifest"]),
        "service_runlevel": {},
        "watchdog": {},
        "carrier_readback": {},
        "eud_route": {},
        "ncm": {},
        "typec": {},
        "tcpm": {},
        "native": {},
        "mp2650": {},
        "protection": {},
        "apsd_adc": {},
        "kernel_log": {},
        "fixed_5v_only": True,
        "accepted": False,
    }


def make_audit_tree(fixture: dict) -> dict:
    sys_root = fixture["base"] / "sys"
    write(sys_root / "class/net/usb0/device/driver/name", "cdc_ncm\n")
    typec_binding = sys_root / "test-typec-binding"
    write(typec_binding / "marker", "bound\n")
    write(
        sys_root
        / "firmware/devicetree/base/soc@0/spmi@c440000/pmic@2/typec@1500/realme,apsd-handoff-trial",
        b"\x00\x00\x00\x01",
    )
    write(
        sys_root
        / "firmware/devicetree/base/soc@0/geniqup@8c0000/i2c@884000/charger@5c/typec-supply",
        b"\x00\x00\x01\x5b",
    )
    write(
        sys_root
        / "firmware/devicetree/base/soc@0/spmi@c440000/pmic@2/adc@3100/channel@8/label",
        b"usb_in_v_div_16\x00",
    )
    write(
        sys_root / "firmware/devicetree/base/soc@0/serial@88e0000/status",
        b"disabled\x00",
    )
    write(
        sys_root / "firmware/devicetree/base/soc@0/eud-off-route/status",
        b"okay\x00",
    )
    eud_route_binding = sys_root / "test-eud-route-binding"
    write(eud_route_binding / "marker", "bound\n")
    adc = sys_root / "bus/iio/devices/iio-device0"
    write(adc / "name", "c440000.spmi:pmic@2:adc@3100\n")
    write(adc / "in_voltage_usb_in_v_div_16_label", "usb_in_v_div_16\n")
    write(adc / "in_voltage_usb_in_v_div_16_input", "4511408\n")
    port = sys_root / "class/typec/port0"
    write(port / "power_role", "[sink] source\n")
    write(port / "data_role", "[device] host\n")
    write(port / "power_operation_mode", "default\n")
    (port.parent / "port0-partner").mkdir(parents=True, exist_ok=True)
    write(port / "connector/sink-pdos", "04019032\n")
    ps = sys_root / "class/power_supply"
    tcpm = ps / "tcpm-source-psy-0-0000"
    write(tcpm / "online", "1\n")
    write(tcpm / "usb_type", "[C] PD\n")
    write(tcpm / "voltage_now", "5000000\n")
    write(tcpm / "current_max", "500000\n")
    write(tcpm / "current_now", "500000\n")
    write(ps / "samurai-usb-input/online", "1\n")
    write(ps / "samurai-usb-input/usb_type", "[SDP]\n")
    write(ps / "samurai-usb-input/current_max", "500000\n")
    write(ps / "mp2650-input/input_current_limit", "900000\n")
    write(ps / "mp2650-input/constant_charge_current", "250000\n")
    write(ps / "mp2650-input/constant_charge_voltage", "8725000\n")
    write(ps / "mp2650-input/health", "Good\n")
    write(ps / "mp2650-input/charge_behaviour", "[auto] inhibit-charge\n")
    write(ps / "samurai-gauge-protection/health", "Good\n")
    write(
        sys_root / "devices/platform/samurai-gauge-protection/protection_state",
        "id=0x2719 safety=0 pf=0 error=0\n",
    )
    write(fixture["proc"] / "sys/kernel/tainted", "4096\n")
    dmesg = "\n".join(
        [
            "[ 0.9] qcom,pmic-typec c440000.spmi:pmic@2:typec@1500: probe bound",
            "[ 1.1] cdc_ncm 2-1:1.0: CDC NCM usb0",
            "[ 1.3] samurai-usb-input: SDP 500mA",
        ]
    )
    status = {
        "managed": True,
        "sample": {
            "shadow": 0,
            "valid": 1,
            "online": 1,
            "protection_ok": 1,
            "budget_ua": 500000,
            "desired_enable": 1,
            "age_ms": 10,
            "logical_full": 0,
            "full_holding": 0,
            "hold_requested": 0,
            "full_cause": 0,
            "fault": 0,
            "error": 0,
            "stop_error": 0,
            "latched": 0,
            "cycle_timeout": 0,
            "thermal_inhibit": 0,
            "source_inhibit": 0,
            "gauge_charge_stop": 0,
        },
    }
    return {
        "sys_root": sys_root,
        "typec_binding": typec_binding,
        "eud_route_binding": eud_route_binding,
        "dmesg": dmesg,
        "status": status,
    }


def audit_runtime(fixture: dict, tree: dict, *, version: str = None) -> postboot_audit.AuditRuntime:
    return postboot_audit.AuditRuntime(
        root=fixture["root"],
        proc_root=fixture["proc"],
        sys_root=tree["sys_root"],
        target_root=fixture["target"],
        manifest_path=fixture["target_manifest"],
        version_reader=lambda: version or trial_common.VERSION,
        boot_id_reader=lambda: NEW_BOOT_ID,
        dmesg_reader=lambda: tree["dmesg"],
        status_reader=lambda: json.loads(json.dumps(tree["status"])),
        require_symlinks=False,
        typec_binding_path=tree["typec_binding"],
        eud_route_binding_path=tree["eud_route_binding"],
        strict_carrier_pins=False,
        partition_bytes=SMALL_BYTES,
        boottime=lambda: 11.0,
        runlevel_reader=lambda: runlevel_current_record(fixture),
    )


class GuardStageTests(unittest.TestCase):
    def test_stage_does_not_use_busybox_reboot_bootloader(self) -> None:
        source = (TRIAL_DIR / "trial_stage.py").read_text()
        self.assertNotIn('"/system/bin/reboot"', source)
        self.assertNotIn('"/sbin/reboot"', source)
        self.assertNotIn('"/usr/sbin/reboot"', source)
        self.assertIn("RESTART2_SYSCALL = 142", source)

    def test_stage_preflight_is_noninstalling_and_nonwriting_to_carriers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fixture(Path(temporary))
            before_devices = {name: path.read_bytes() for name, path in fixture["devices"].items()}
            calls = []
            runtime = trial_stage.StageRuntime(
                package=fixture["package"],
                root=fixture["root"],
                proc_root=fixture["proc"],
                target_root=fixture["target"],
                manifest_path=fixture["manifest_path"],
                devices=fixture["devices"],
                identities=fixture["identities"],
                require_root=False,
                strict_carrier_pins=False,
                partition_bytes=SMALL_BYTES,
                serial_reader=lambda: "",
                service_stopper=lambda: {"returncode": 0, "stdout": {"managed": False}},
                syncer=lambda: None,
                fsyncer=lambda paths: None,
                bootloader_restarter=lambda: calls.append("restart2"),
                **runlevel_kwargs(fixture),
            )
            receipt = trial_stage.stage(
                runtime, execute=False, operator_serial=SERIAL
            )
            self.assertFalse(receipt["guard_installed"])
            self.assertFalse(receipt["old_carriers_backed_up"])
            self.assertEqual(receipt["serial_source"], "operator_cli")
            self.assertFalse((fixture["root"] / "original/samurai-charging").exists())
            self.assertFalse((fixture["root"] / "original/main-manifest.json").exists())
            self.assertFalse((fixture["root"] / "original/samurai-mp2650.ko").exists())
            self.assertEqual(fixture["original_service"].read_text(), "#!/sbin/openrc-run\n# original service\n")
            self.assertEqual(
                sha(
                    fixture["target"]
                    / Path(str(trial_common.MODULE_PATH)).relative_to("/")
                ),
                fixture["original_module_sha256"],
            )
            self.assertEqual(
                sha(fixture["main_manifest"]),
                fixture["original_main_manifest_sha256"],
            )
            self.assertEqual(before_devices, {name: path.read_bytes() for name, path in fixture["devices"].items()})
            self.assertEqual(calls, [])

    def test_stage_backs_up_only_and_installs_guard_service(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fixture(Path(temporary))
            before_devices = {name: path.read_bytes() for name, path in fixture["devices"].items()}
            stage_fixture(fixture)
            self.assertEqual(
                before_devices,
                {name: path.read_bytes() for name, path in fixture["devices"].items()},
            )
            self.assertEqual(fixture["stage_reboot_calls"], ["restart2"])
            self.assertEqual(
                (fixture["root"] / "old/boot.img").read_bytes(),
                fixture["old_paths"]["boot"].read_bytes(),
            )
            self.assertEqual(
                (fixture["root"] / "old/logdump.img").read_bytes(),
                fixture["old_paths"]["logdump"].read_bytes(),
            )
            receipt = json.loads((fixture["root"] / "stage-result.json").read_text())
            self.assertTrue(receipt["guard_installed"])
            self.assertTrue(receipt["old_carriers_backed_up"])
            self.assertEqual(receipt["serial_source"], "operator_cli")
            self.assertFalse(receipt["new_carrier_written"])
            self.assertTrue(receipt["reboot_bootloader_requested"])
            self.assertNotEqual(
                sha(fixture["target"] / "etc/init.d/samurai-charging"),
                fixture["original_service_sha256"],
            )
            installed_service = sha(fixture["target"] / "etc/init.d/samurai-charging")
            main_value = json.loads(fixture["main_manifest"].read_text())
            self.assertEqual(
                main_value["installed_files"][
                    trial_common.SERVICE_PATH.as_posix()
                ],
                installed_service,
            )
            self.assertNotEqual(
                sha(fixture["main_manifest"]),
                fixture["original_main_manifest_sha256"],
            )
            self.assertEqual(
                (fixture["root"] / "original/main-manifest.json").read_bytes(),
                fixture["original_main_manifest_bytes"],
            )
            self.assertEqual(
                (fixture["root"] / "original/samurai-mp2650.ko").read_bytes(),
                fixture["original_module_bytes"],
            )
            self.assertEqual(
                sha(
                    fixture["target"]
                    / Path(str(trial_common.MODULE_PATH)).relative_to("/")
                ),
                fixture["new_module_sha256"],
            )
            self.assertEqual(
                main_value["modules"][trial_common.MODULE_NAME]["sha256"],
                fixture["new_module_sha256"],
            )
            self.assertEqual(
                main_value["installed_files"][
                    trial_common.MODULE_PATH.as_posix()
                ],
                fixture["new_module_sha256"],
            )
            self.assertTrue(receipt["module_installed"])
            self.assertEqual(
                receipt["original_module"]["sha256"],
                fixture["original_module_sha256"],
            )
            self.assertEqual(
                receipt["service_runlevel"],
                {
                    "target": trial_common.RUNLEVEL_PATH.as_posix(),
                    "before": "missing",
                    "added": True,
                    "link_target": trial_common.SERVICE_PATH.as_posix(),
                    "verified": True,
                },
            )
            self.assertTrue(fixture["runlevel_state"]["present"])

    def test_stage_does_not_touch_an_existing_default_runlevel_link(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fixture(Path(temporary))
            fixture["runlevel_state"].update(
                present=True,
                link_target=trial_common.SERVICE_PATH.as_posix(),
            )
            stage_fixture(fixture)
            self.assertEqual(fixture["runlevel_state"]["enable_calls"], 0)
            self.assertTrue(fixture["runlevel_state"]["present"])
            self.assertEqual(
                fixture["receipt"]["service_runlevel"]["before"],
                "enabled",
            )
            self.assertFalse(fixture["receipt"]["service_runlevel"]["added"])

    def test_stage_rejects_non_symlink_runlevel_before_device_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fixture(Path(temporary))
            runlevel = (
                fixture["target"]
                / trial_common.RUNLEVEL_PATH.relative_to("/")
            )
            write(runlevel, "not a symlink\n")
            events = []
            runtime = trial_stage.StageRuntime(
                package=fixture["package"],
                root=fixture["root"],
                proc_root=fixture["proc"],
                target_root=fixture["target"],
                manifest_path=fixture["manifest_path"],
                devices=fixture["devices"],
                identities=fixture["identities"],
                require_root=False,
                strict_carrier_pins=False,
                partition_bytes=SMALL_BYTES,
                serial_reader=lambda: "",
                service_stopper=lambda: events.append("stop"),
                syncer=lambda: None,
                fsyncer=lambda paths: None,
                bootloader_restarter=lambda: events.append("restart2"),
            )
            with self.assertRaisesRegex(
                trial_common.TrialError,
                "missing or a symlink",
            ):
                trial_stage.stage(
                    runtime,
                    execute=True,
                    operator_serial=SERIAL,
                )
            self.assertEqual(events, [])
            self.assertFalse((fixture["root"] / "stage-plan.json").exists())
            self.assertEqual(
                sha(fixture["target"] / "etc/init.d/samurai-charging"),
                fixture["original_service_sha256"],
            )
            self.assertEqual(
                sha(fixture["main_manifest"]),
                fixture["original_main_manifest_sha256"],
            )

    def test_guard_does_not_arm_on_the_old_stage_boot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fixture(Path(temporary))
            stage_fixture(fixture)
            runtime = guard_runtime(fixture)
            with mock.patch.object(trial_guard, "start_watch") as start_watch:
                trial_guard.prestart(runtime, version_reader=lambda: OLD_VERSION)
            start_watch.assert_not_called()
            state = json.loads((fixture["root"] / "state.json").read_text())
            self.assertEqual(state["event"], "stage-pending-host-reboot")

    def test_guard_timeout_restores_boot_then_logdump_then_original_service(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fixture(Path(temporary))
            stage_fixture(fixture)
            new_boot(fixture)
            reboot_calls = []
            runtime = guard_runtime(fixture, reboot_calls=reboot_calls)
            with mock.patch.object(trial_guard, "start_watch") as start_watch:
                trial_guard.prestart(runtime, version_reader=lambda: trial_common.VERSION)
            self.assertTrue(start_watch.called)
            deadline = start_watch.call_args.args[1]
            self.assertEqual(deadline, 100.0 + trial_common.WATCH_SECONDS)
            order = []
            original = trial_guard.write_carrier_from_backup

            def record_order(rt, stage, name, digest):
                order.append(name)
                return original(rt, stage, name, digest)

            with mock.patch.object(
                trial_guard, "write_carrier_from_backup", side_effect=record_order
            ):
                trial_guard.watch(runtime, deadline_boottime=50.0)
            self.assertEqual(order, ["boot", "logdump"])
            self.assertEqual(reboot_calls, ["reboot"])
            for name in SMALL_BYTES:
                self.assertEqual(
                    fixture["devices"][name].read_bytes(),
                    fixture["old_paths"][name].read_bytes(),
                )
            self.assertEqual(
                fixture["original_service_sha256"],
                sha(fixture["target"] / "etc/init.d/samurai-charging"),
            )
            self.assertEqual(
                fixture["original_main_manifest_sha256"],
                sha(fixture["main_manifest"]),
            )
            self.assertEqual(
                fixture["original_module_sha256"],
                sha(
                    fixture["target"]
                    / Path(str(trial_common.MODULE_PATH)).relative_to("/")
                ),
            )
            rollback = json.loads((fixture["root"] / "rollback.json").read_text())
            self.assertTrue(rollback["main_manifest_restored"])
            self.assertTrue(rollback["original_module_restored"])
            self.assertEqual(
                rollback["module_sha256"],
                fixture["original_module_sha256"],
            )
            self.assertEqual(
                rollback["main_manifest_sha256"],
                fixture["original_main_manifest_sha256"],
            )
            self.assertTrue(rollback["service_runlevel_restored"])
            self.assertFalse(fixture["runlevel_state"]["present"])
            self.assertEqual(fixture["runlevel_state"]["restore_calls"], 1)

    def test_guard_rollback_keeps_a_preexisting_runlevel_link(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fixture(Path(temporary))
            fixture["runlevel_state"].update(
                present=True,
                link_target=trial_common.SERVICE_PATH.as_posix(),
            )
            stage_fixture(fixture)
            new_boot(fixture)
            runtime = guard_runtime(fixture)
            with mock.patch.object(trial_guard, "start_watch"):
                trial_guard.prestart(runtime)
            trial_guard.watch(runtime, deadline_boottime=50.0)
            self.assertTrue(fixture["runlevel_state"]["present"])
            self.assertEqual(fixture["runlevel_state"]["enable_calls"], 0)
            self.assertEqual(fixture["runlevel_state"]["restore_calls"], 1)

    def test_guard_restores_through_by_partlabel_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fixture(Path(temporary))
            stage_fixture(fixture)
            new_boot(fixture)
            runtime = guard_runtime(fixture)
            link = fixture["base"] / "devices/by-partlabel-boot"
            try:
                link.symlink_to(fixture["devices"]["boot"])
            except OSError as error:
                if os.name == "nt" and getattr(error, "winerror", None) == 1314:
                    self.skipTest("Windows symlink privilege is unavailable")
                raise
            runtime.devices["boot"] = link
            stage = json.loads((fixture["root"] / "stage.json").read_text())
            trial_guard.write_carrier_from_backup(
                runtime,
                stage,
                "boot",
                fixture["manifest"]["carriers"]["boot"]["old"],
            )
            self.assertTrue(link.is_symlink())
            self.assertEqual(
                fixture["devices"]["boot"].read_bytes(),
                fixture["old_paths"]["boot"].read_bytes(),
            )

    def test_stage_rejects_unpinned_original_module_before_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fixture(Path(temporary))
            module_target = (
                fixture["target"]
                / Path(str(trial_common.MODULE_PATH)).relative_to("/")
            )
            module_target.write_bytes(fixture["new_module"].read_bytes())
            runtime = make_stage_runtime(fixture)
            with self.assertRaisesRegex(
                trial_common.TrialError,
                "original module",
            ):
                trial_stage.stage(runtime, execute=True, operator_serial=SERIAL)
            self.assertFalse((fixture["root"] / "stage-plan.json").exists())
            self.assertEqual(
                sha(fixture["target"] / "etc/init.d/samurai-charging"),
                fixture["original_service_sha256"],
            )
            self.assertEqual(
                sha(fixture["main_manifest"]),
                fixture["original_main_manifest_sha256"],
            )

    def test_stage_rejects_main_manifest_module_pin_tamper(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fixture(Path(temporary))
            value = json.loads(fixture["main_manifest"].read_text())
            value["modules"][trial_common.MODULE_NAME]["sha256"] = "0" * 64
            write(
                fixture["main_manifest"],
                json.dumps(value, indent=2, sort_keys=True) + "\n",
            )
            manifest = json.loads(fixture["manifest_path"].read_text())
            manifest["main_manifest"]["old_sha256"] = sha(fixture["main_manifest"])
            write(
                fixture["manifest_path"],
                json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            )
            runtime = make_stage_runtime(fixture)
            with self.assertRaisesRegex(
                trial_common.TrialError,
                "main manifest does not pin the original module",
            ):
                trial_stage.stage(runtime, execute=True, operator_serial=SERIAL)
            self.assertFalse((fixture["root"] / "stage-plan.json").exists())

    def test_stage_module_install_failure_restores_all_originals(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fixture(Path(temporary))
            runtime = make_stage_runtime(fixture)
            original_install = trial_stage._install_module

            def fail_after_install(rt, manifest):
                original_install(rt, manifest)
                raise trial_common.TrialError("module install failed")

            with mock.patch.object(
                trial_stage,
                "_install_module",
                side_effect=fail_after_install,
            ):
                with self.assertRaisesRegex(
                    trial_common.TrialError,
                    "module install failed",
                ):
                    trial_stage.stage(
                        runtime,
                        execute=True,
                        operator_serial=SERIAL,
                    )
            self.assertEqual(
                sha(
                    fixture["target"]
                    / Path(str(trial_common.MODULE_PATH)).relative_to("/")
                ),
                fixture["original_module_sha256"],
            )
            self.assertEqual(
                sha(fixture["target"] / "etc/init.d/samurai-charging"),
                fixture["original_service_sha256"],
            )
            self.assertEqual(
                fixture["main_manifest"].read_bytes(),
                fixture["original_main_manifest_bytes"],
            )
            failure = json.loads((fixture["root"] / "stage-failure.json").read_text())
            self.assertTrue(failure["restored_original_files"])
            self.assertFalse(fixture["target_manifest"].exists())

    def test_stage_explicit_serial_is_operator_assertion(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fixture(Path(temporary))
            calls = []
            runtime = trial_stage.StageRuntime(
                package=fixture["package"],
                root=fixture["root"],
                proc_root=fixture["proc"],
                target_root=fixture["target"],
                manifest_path=fixture["manifest_path"],
                devices=fixture["devices"],
                identities=fixture["identities"],
                require_root=False,
                strict_carrier_pins=False,
                partition_bytes=SMALL_BYTES,
                serial_reader=lambda: "",
                service_stopper=lambda: {"returncode": 0, "stdout": {"managed": False}},
                syncer=lambda: None,
                fsyncer=lambda paths: None,
                bootloader_restarter=lambda: calls.append("restart2"),
                **runlevel_kwargs(fixture),
            )
            receipt = trial_stage.stage(
                runtime, execute=True, operator_serial=SERIAL
            )
            self.assertEqual(receipt["serial"], SERIAL)
            self.assertEqual(receipt["serial_source"], "operator_cli")

    def test_stage_stops_and_fsyncs_before_install_then_restart2_once(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fixture(Path(temporary))
            events = []
            fsync_calls = []
            restart_calls = []
            stop_was_original = []

            def stopper():
                events.append("stop")
                stop_was_original.append(
                    sha(fixture["target"] / "etc/init.d/samurai-charging")
                    == fixture["original_service_sha256"]
                )
                return {"returncode": 0, "stdout": {"managed": False}}

            def syncer():
                events.append("sync")

            def fsyncer(paths):
                fsync_calls.append([str(path) for path in paths])
                events.append("fsync")

            def restarter():
                restart_calls.append("restart2")
                events.append("restart2")

            runtime = trial_stage.StageRuntime(
                package=fixture["package"],
                root=fixture["root"],
                proc_root=fixture["proc"],
                target_root=fixture["target"],
                manifest_path=fixture["manifest_path"],
                devices=fixture["devices"],
                identities=fixture["identities"],
                require_root=False,
                strict_carrier_pins=False,
                partition_bytes=SMALL_BYTES,
                serial_reader=lambda: "",
                service_stopper=stopper,
                syncer=syncer,
                fsyncer=fsyncer,
                bootloader_restarter=restarter,
                **runlevel_kwargs(fixture),
            )
            receipt = trial_stage.stage(
                runtime, execute=True, operator_serial=SERIAL
            )
            self.assertEqual(
                events,
                ["stop", "sync", "fsync", "sync", "fsync", "restart2"],
            )
            self.assertEqual(stop_was_original, [True])
            self.assertEqual(restart_calls, ["restart2"])
            self.assertEqual(
                receipt["restart_method"], "restart2_syscall_142"
            )
            self.assertEqual(receipt["restart2"]["syscall"], 142)
            self.assertEqual(receipt["restart2"]["magic1"], 0xFEE1DEAD)
            self.assertEqual(receipt["restart2"]["magic2"], 672274793)
            self.assertEqual(receipt["restart2"]["command_value"], 0xA1B2C3D4)
            self.assertFalse(receipt["restart2"]["retry"])
            self.assertEqual(len(fsync_calls), 2)
            self.assertTrue(
                any(path.endswith("old\\boot.img") or path.endswith("old/boot.img") for path in fsync_calls[0])
            )
            self.assertTrue(
                any(path.endswith("stage-result.json") for path in fsync_calls[1])
            )

    def test_stage_receipt_records_host_fetch_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fixture(Path(temporary))
            manifest = json.loads(fixture["manifest_path"].read_text())
            manifest["fastboot"]["host_fetch_unavailable"] = True
            write(
                fixture["manifest_path"],
                json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            )
            stage_fixture(fixture)
            self.assertIs(fixture["receipt"]["host_fetch_unavailable"], True)

    def test_restart2_syscall_uses_verified_aarch64_arguments(self) -> None:
        seen = {}

        def fake_syscall(number, magic1, magic2, command, pointer):
            seen.update(
                number=number,
                magic1=magic1,
                magic2=magic2,
                command=command,
                text=ctypes.string_at(pointer),
            )
            return 0

        with self.assertRaisesRegex(
            trial_common.TrialError, "Restart2 bootloader syscall returned"
        ):
            trial_stage.restart2_bootloader(
                machine="aarch64", syscall_fn=fake_syscall
            )
        self.assertEqual(
            seen,
            {
                "number": 142,
                "magic1": 0xFEE1DEAD,
                "magic2": 672274793,
                "command": 0xA1B2C3D4,
                "text": b"bootloader",
            },
        )
        with self.assertRaisesRegex(
            trial_common.TrialError, "requires AArch64"
        ):
            trial_stage.restart2_bootloader(
                machine="x86_64", syscall_fn=fake_syscall
            )

    def test_stage_stop_failure_prevents_install_and_restart(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fixture(Path(temporary))
            restart_calls = []
            runtime = trial_stage.StageRuntime(
                package=fixture["package"],
                root=fixture["root"],
                proc_root=fixture["proc"],
                target_root=fixture["target"],
                manifest_path=fixture["manifest_path"],
                devices=fixture["devices"],
                identities=fixture["identities"],
                require_root=False,
                strict_carrier_pins=False,
                partition_bytes=SMALL_BYTES,
                serial_reader=lambda: "",
                service_stopper=lambda: (_ for _ in ()).throw(
                    trial_common.TrialError("stop failed")
                ),
                syncer=lambda: None,
                fsyncer=lambda paths: None,
                bootloader_restarter=lambda: restart_calls.append("restart2"),
                **runlevel_kwargs(fixture),
            )
            with self.assertRaisesRegex(trial_common.TrialError, "stop failed"):
                trial_stage.stage(
                    runtime, execute=True, operator_serial=SERIAL
                )
            self.assertFalse(fixture["target_manifest"].exists())
            self.assertEqual(restart_calls, [])
            self.assertEqual(
                sha(fixture["target"] / "etc/init.d/samurai-charging"),
                fixture["original_service_sha256"],
            )
            self.assertEqual(
                sha(fixture["main_manifest"]),
                fixture["original_main_manifest_sha256"],
            )
            self.assertEqual(
                sha(
                    fixture["target"]
                    / Path(str(trial_common.MODULE_PATH)).relative_to("/")
                ),
                fixture["original_module_sha256"],
            )

    def test_stage_restart2_failure_is_not_retried(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fixture(Path(temporary))
            calls = []

            def failed_restart():
                calls.append("restart2")
                raise trial_common.TrialError("syscall returned")

            runtime = trial_stage.StageRuntime(
                package=fixture["package"],
                root=fixture["root"],
                proc_root=fixture["proc"],
                target_root=fixture["target"],
                manifest_path=fixture["manifest_path"],
                devices=fixture["devices"],
                identities=fixture["identities"],
                require_root=False,
                strict_carrier_pins=False,
                partition_bytes=SMALL_BYTES,
                serial_reader=lambda: "",
                service_stopper=lambda: {"returncode": 0, "stdout": {}},
                syncer=lambda: None,
                fsyncer=lambda paths: None,
                bootloader_restarter=failed_restart,
                **runlevel_kwargs(fixture),
            )
            with self.assertRaisesRegex(
                trial_common.TrialError, "syscall returned"
            ):
                trial_stage.stage(
                    runtime, execute=True, operator_serial=SERIAL
                )
            self.assertEqual(calls, ["restart2"])
            self.assertEqual(
                sha(fixture["target"] / "etc/init.d/samurai-charging"),
                fixture["original_service_sha256"],
            )
            self.assertEqual(
                sha(fixture["main_manifest"]),
                fixture["original_main_manifest_sha256"],
            )
            self.assertFalse((fixture["root"] / "stage-result.json").exists())
            failure = json.loads((fixture["root"] / "stage-failure.json").read_text())
            self.assertTrue(failure["restored_original_files"])
            self.assertFalse(fixture["runlevel_state"]["present"])
            self.assertEqual(fixture["runlevel_state"]["restore_calls"], 1)

    def test_restart2_failure_keeps_a_preexisting_runlevel_link(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fixture(Path(temporary))
            fixture["runlevel_state"].update(
                present=True,
                link_target=trial_common.SERVICE_PATH.as_posix(),
            )

            def failed_restart():
                raise trial_common.TrialError("syscall returned")

            runtime = make_stage_runtime(fixture, restarter=failed_restart)
            with self.assertRaisesRegex(
                trial_common.TrialError,
                "syscall returned",
            ):
                trial_stage.stage(
                    runtime,
                    execute=True,
                    operator_serial=SERIAL,
                )
            self.assertTrue(fixture["runlevel_state"]["present"])
            self.assertEqual(fixture["runlevel_state"]["enable_calls"], 0)
            self.assertEqual(fixture["runlevel_state"]["restore_calls"], 1)

    @unittest.skipIf(os.name == "nt", "real symlink checks run in WSL/Linux")
    def test_default_runlevel_link_reader_and_exact_restore(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fixture(Path(temporary))
            path = (
                fixture["target"]
                / trial_common.RUNLEVEL_PATH.relative_to("/")
            )
            path.parent.mkdir(parents=True)
            self.assertEqual(
                trial_common.inspect_service_runlevel(fixture["target"])["before"],
                "missing",
            )
            path.symlink_to(trial_common.SERVICE_PATH)
            enabled = trial_common.inspect_service_runlevel(fixture["target"])
            self.assertEqual(enabled["before"], "enabled")
            self.assertEqual(
                enabled["link_target"], trial_common.SERVICE_PATH.as_posix()
            )
            fsync_calls = []
            trial_common.restore_service_runlevel(
                fixture["target"],
                {**enabled, "added": False},
                fsync_directory=fsync_calls.append,
            )
            self.assertTrue(path.is_symlink())
            self.assertEqual(fsync_calls, [])
            new_record = {
                "target": trial_common.RUNLEVEL_PATH.as_posix(),
                "before": "missing",
                "added": True,
                "link_target": trial_common.SERVICE_PATH.as_posix(),
                "verified": True,
            }
            restored = trial_common.restore_service_runlevel(
                fixture["target"],
                new_record,
                fsync_directory=fsync_calls.append,
            )
            self.assertTrue(restored["removed"])
            self.assertFalse(path.exists())
            self.assertEqual(fsync_calls, [path.parent])

    @unittest.skipIf(os.name == "nt", "real symlink checks run in WSL/Linux")
    def test_default_runlevel_inspector_rejects_wrong_or_regular_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fixture(Path(temporary))
            path = (
                fixture["target"]
                / trial_common.RUNLEVEL_PATH.relative_to("/")
            )
            path.parent.mkdir(parents=True)
            path.symlink_to("/etc/init.d/wrong")
            with self.assertRaisesRegex(
                trial_common.TrialError,
                "unexpected target",
            ):
                trial_common.inspect_service_runlevel(fixture["target"])
            path.unlink()
            write(path, "regular file\n")
            with self.assertRaisesRegex(
                trial_common.TrialError,
                "missing or a symlink",
            ):
                trial_common.inspect_service_runlevel(fixture["target"])

    @unittest.skipIf(os.name == "nt", "real symlink checks run in WSL/Linux")
    def test_stage_rejects_wrong_symlink_before_device_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fixture(Path(temporary))
            path = (
                fixture["target"]
                / trial_common.RUNLEVEL_PATH.relative_to("/")
            )
            path.parent.mkdir(parents=True)
            path.symlink_to("/etc/init.d/wrong")
            events = []
            runtime = trial_stage.StageRuntime(
                package=fixture["package"],
                root=fixture["root"],
                proc_root=fixture["proc"],
                target_root=fixture["target"],
                manifest_path=fixture["manifest_path"],
                devices=fixture["devices"],
                identities=fixture["identities"],
                require_root=False,
                strict_carrier_pins=False,
                partition_bytes=SMALL_BYTES,
                serial_reader=lambda: "",
                service_stopper=lambda: events.append("stop"),
                syncer=lambda: None,
                fsyncer=lambda paths: None,
                bootloader_restarter=lambda: events.append("restart2"),
            )
            with self.assertRaisesRegex(
                trial_common.TrialError,
                "unexpected target",
            ):
                trial_stage.stage(
                    runtime,
                    execute=True,
                    operator_serial=SERIAL,
                )
            self.assertEqual(events, [])
            self.assertFalse((fixture["root"] / "stage-plan.json").exists())

    @unittest.skipIf(os.name == "nt", "real symlink checks run in WSL/Linux")
    def test_default_runlevel_enabler_uses_fixed_argv_and_skips_existing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fixture(Path(temporary))
            path = (
                fixture["target"]
                / trial_common.RUNLEVEL_PATH.relative_to("/")
            )
            path.parent.mkdir(parents=True)
            fsync_calls = []
            runtime = make_stage_runtime(
                fixture,
                fsyncer=lambda paths: fsync_calls.append(paths),
            )
            missing = trial_common.inspect_service_runlevel(fixture["target"])

            def run(argv, **kwargs):
                self.assertEqual(
                    argv,
                    ["/sbin/rc-update", "add", "samurai-charging", "default"],
                )
                self.assertEqual(kwargs["timeout"], 20)
                path.symlink_to(trial_common.SERVICE_PATH)
                return subprocess.CompletedProcess(argv, 0, "", "")

            with mock.patch.object(trial_stage.subprocess, "run", side_effect=run):
                added = trial_stage._default_enable_service_runlevel(
                    runtime,
                    missing,
                )
            self.assertTrue(added["added"])
            self.assertEqual(fsync_calls, [[path.parent]])
            current = trial_common.inspect_service_runlevel(fixture["target"])
            with mock.patch.object(trial_stage.subprocess, "run") as command:
                existing = trial_stage._default_enable_service_runlevel(
                    runtime,
                    current,
                )
            command.assert_not_called()
            self.assertFalse(existing["added"])

    def test_stage_requires_serial_when_device_exposes_none(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fixture(Path(temporary))
            runtime = trial_stage.StageRuntime(
                package=fixture["package"],
                root=fixture["root"],
                proc_root=fixture["proc"],
                target_root=fixture["target"],
                manifest_path=fixture["manifest_path"],
                devices=fixture["devices"],
                identities=fixture["identities"],
                require_root=False,
                strict_carrier_pins=False,
                partition_bytes=SMALL_BYTES,
                serial_reader=lambda: "",
                service_stopper=lambda: {"returncode": 0, "stdout": {"managed": False}},
                syncer=lambda: None,
                fsyncer=lambda paths: None,
                bootloader_restarter=lambda: None,
                **runlevel_kwargs(fixture),
            )
            with self.assertRaisesRegex(
                trial_common.TrialError, "rerun with --serial 62bc28a1"
            ):
                trial_stage.stage(runtime, execute=False)

    def test_stage_rejects_extra_device_file_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fixture(Path(temporary))
            manifest = json.loads(fixture["manifest_path"].read_text())
            manifest["device_files"]["/etc/unexpected"] = {
                "source": "trial_common.py",
                "target": "/etc/unexpected",
                "mode": 0o644,
                "sha256": sha(fixture["package"] / "trial_common.py"),
            }
            write(
                fixture["manifest_path"],
                json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            )
            runtime = trial_stage.StageRuntime(
                package=fixture["package"],
                root=fixture["root"],
                proc_root=fixture["proc"],
                target_root=fixture["target"],
                manifest_path=fixture["manifest_path"],
                devices=fixture["devices"],
                identities=fixture["identities"],
                require_root=False,
                strict_carrier_pins=False,
                partition_bytes=SMALL_BYTES,
                serial_reader=lambda: "",
                service_stopper=lambda: {"returncode": 0, "stdout": {}},
                syncer=lambda: None,
                fsyncer=lambda paths: None,
                bootloader_restarter=lambda: None,
                **runlevel_kwargs(fixture),
            )
            with self.assertRaisesRegex(
                trial_common.TrialError, "exactly the formal trial files"
            ):
                trial_stage.stage(runtime, execute=False, operator_serial=SERIAL)

    def test_guard_accepts_only_a_token_for_the_current_boot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fixture(Path(temporary))
            stage_fixture(fixture)
            new_boot(fixture)
            reboot_calls = []
            runtime = guard_runtime(fixture, reboot_calls=reboot_calls)
            trial_autoaudit.record_acceptance(
                complete_report(fixture),
                root=fixture["root"],
                manifest_path=fixture["target_manifest"],
                boot_id_reader=lambda: NEW_BOOT_ID,
                require_root=False,
            )
            trial_guard.watch(runtime, deadline_boottime=200.0)
            self.assertEqual(reboot_calls, [])
            for name in SMALL_BYTES:
                self.assertEqual(
                    fixture["devices"][name].read_bytes(),
                    fixture["new_paths"][name].read_bytes(),
                )
            write(fixture["proc"] / "sys/kernel/random/boot_id", OTHER_BOOT_ID + "\n")
            trial_guard.watch(runtime, deadline_boottime=50.0)
            self.assertEqual(reboot_calls, ["reboot"])
            self.assertEqual(
                fixture["devices"]["boot"].read_bytes(),
                fixture["old_paths"]["boot"].read_bytes(),
            )

    def test_guard_rejects_main_manifest_not_bound_to_trial_service(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fixture(Path(temporary))
            stage_fixture(fixture)
            value = json.loads(fixture["main_manifest"].read_text())
            value["installed_files"][
                trial_common.SERVICE_PATH.as_posix()
            ] = "0" * 64
            write(
                fixture["main_manifest"],
                json.dumps(value, indent=2, sort_keys=True) + "\n",
            )
            with self.assertRaisesRegex(
                trial_common.TrialError,
                "main manifest does not pin the trial file",
            ):
                trial_guard.verify_installed(
                    guard_runtime(fixture),
                    trial_guard.load_manifest(guard_runtime(fixture)),
                )

    def test_guard_rejects_installed_module_hash_tamper(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fixture(Path(temporary))
            stage_fixture(fixture)
            module_target = (
                fixture["target"]
                / Path(str(trial_common.MODULE_PATH)).relative_to("/")
            )
            module_target.write_bytes(b"tampered-module" + b"\0" * 177)
            runtime = guard_runtime(fixture)
            with self.assertRaisesRegex(
                trial_common.TrialError,
                "installed module hash mismatch",
            ):
                trial_guard.verify_installed(
                    runtime,
                    trial_guard.load_manifest(runtime),
                )

    def test_guard_rejects_main_manifest_module_hash_tamper(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fixture(Path(temporary))
            stage_fixture(fixture)
            value = json.loads(fixture["main_manifest"].read_text())
            value["modules"][trial_common.MODULE_NAME]["sha256"] = "0" * 64
            write(
                fixture["main_manifest"],
                json.dumps(value, indent=2, sort_keys=True) + "\n",
            )
            runtime = guard_runtime(fixture)
            with self.assertRaisesRegex(
                trial_common.TrialError,
                "main manifest does not pin the trial module",
            ):
                trial_guard.verify_installed(
                    runtime,
                    trial_guard.load_manifest(runtime),
                )

    def test_guard_prestart_new_pair_failure_rolls_back(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fixture(Path(temporary))
            stage_fixture(fixture)
            new_boot(fixture)
            fixture["devices"]["boot"].write_bytes(b"corrupt-new-boot" + b"\0" * 80)
            reboot_calls = []
            trial_guard.prestart(
                guard_runtime(fixture, reboot_calls=reboot_calls)
            )
            self.assertEqual(reboot_calls, ["reboot"])
            for name in SMALL_BYTES:
                self.assertEqual(
                    fixture["devices"][name].read_bytes(),
                    fixture["old_paths"][name].read_bytes(),
                )
            self.assertEqual(
                fixture["original_service"].read_bytes(),
                fixture["original_service_bytes"],
            )
            self.assertEqual(
                fixture["main_manifest"].read_bytes(),
                fixture["original_main_manifest_bytes"],
            )
            self.assertEqual(
                sha(
                    fixture["target"]
                    / Path(str(trial_common.MODULE_PATH)).relative_to("/")
                ),
                fixture["original_module_sha256"],
            )

    def test_guard_prestart_watchdog_failure_rolls_back(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fixture(Path(temporary))
            stage_fixture(fixture)
            new_boot(fixture)
            reboot_calls = []
            runtime = guard_runtime(fixture, reboot_calls=reboot_calls)
            with mock.patch.object(
                trial_guard,
                "start_watch",
                side_effect=trial_common.TrialError("watchdog spawn failed"),
            ):
                trial_guard.prestart(runtime)
            self.assertEqual(reboot_calls, ["reboot"])
            for name in SMALL_BYTES:
                self.assertEqual(
                    fixture["devices"][name].read_bytes(),
                    fixture["old_paths"][name].read_bytes(),
                )


class PostbootAuditTests(unittest.TestCase):
    def _ready(self, temporary: str) -> tuple[dict, dict]:
        fixture = make_fixture(Path(temporary))
        stage_fixture(fixture)
        new_boot(fixture)
        write_watchdog_state(fixture)
        runtime = guard_runtime(fixture)
        readback = trial_guard.verify_new_pair(
            runtime,
            trial_guard.load_manifest(runtime),
            json.loads((fixture["root"] / "stage.json").read_text()),
        )
        trial_common.atomic_write(
            fixture["root"] / "carrier-readback.json",
            (json.dumps(readback, sort_keys=True) + "\n").encode(),
        )
        tree = make_audit_tree(fixture)
        return fixture, tree

    def test_good_postboot_audit_is_read_only_and_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture, tree = self._ready(temporary)
            before = snapshot(fixture["base"])
            report = postboot_audit.audit(audit_runtime(fixture, tree))
            after = snapshot(fixture["base"])
            self.assertTrue(report["passed"], report)
            self.assertTrue(report["read_only"])
            self.assertFalse(report["accepted_token_written"])
            self.assertTrue(report["fixed_5v_only"])
            self.assertFalse(report["high_voltage_accessed"])
            self.assertEqual(before, after)
            self.assertEqual(
                report["service_runlevel"]["link_target"],
                trial_common.SERVICE_PATH.as_posix(),
            )

    def test_audit_rejects_missing_default_runlevel_link(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture, tree = self._ready(temporary)
            fixture["runlevel_state"].update(present=False, link_target=None)
            report = postboot_audit.audit(audit_runtime(fixture, tree))
            self.assertFalse(report["passed"])
            self.assertIn("runlevel", report["error"])

    def test_audit_rejects_wrong_default_runlevel_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture, tree = self._ready(temporary)
            fixture["runlevel_state"]["link_target"] = "/etc/init.d/wrong"
            report = postboot_audit.audit(audit_runtime(fixture, tree))
            self.assertFalse(report["passed"])
            self.assertIn("runlevel", report["error"])

    def test_audit_rejects_wrong_version(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture, tree = self._ready(temporary)
            report = postboot_audit.audit(
                audit_runtime(fixture, tree, version="#514 SMP PREEMPT")
            )
            self.assertFalse(report["passed"])
            self.assertIn("kernel version", report["error"])

    def test_audit_rejects_boot_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture, tree = self._ready(temporary)
            write_watchdog_state(fixture, boot_id=OLD_BOOT_ID)
            report = postboot_audit.audit(audit_runtime(fixture, tree))
            self.assertFalse(report["passed"])
            self.assertIn("different boot", report["error"])

    def test_audit_requires_guard_carrier_readback_for_same_boot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture, tree = self._ready(temporary)
            readback = json.loads(
                (fixture["root"] / "carrier-readback.json").read_text()
            )
            readback["boot_id"] = OLD_BOOT_ID
            write(
                fixture["root"] / "carrier-readback.json",
                json.dumps(readback, sort_keys=True) + "\n",
            )
            report = postboot_audit.audit(audit_runtime(fixture, tree))
            self.assertFalse(report["passed"])
            self.assertIn("carrier readback evidence", report["error"])

    def test_audit_rejects_dead_watchdog_process(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture, tree = self._ready(temporary)
            write(
                fixture["proc"] / "4242/stat",
                "4242 (python3) Z 1 4242 4242 0 -1 0 0 0 0 0 0 0 0 20 0 1 0 1 0 0\n",
            )
            report = postboot_audit.audit(audit_runtime(fixture, tree))
            self.assertFalse(report["passed"])
            self.assertIn("watchdog process", report["error"])

    def test_audit_rejects_missing_ncm_binding(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture, tree = self._ready(temporary)
            write(tree["sys_root"] / "class/net/usb0/device/driver/name", "rndis_host\n")
            report = postboot_audit.audit(audit_runtime(fixture, tree))
            self.assertFalse(report["passed"])
            self.assertIn("USB gadget NCM", report["error"])

    def test_audit_rejects_enabled_eud_com(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture, tree = self._ready(temporary)
            write(
                tree["sys_root"]
                / "firmware/devicetree/base/soc@0/serial@88e0000/status",
                b"okay\x00",
            )
            report = postboot_audit.audit(audit_runtime(fixture, tree))
            self.assertFalse(report["passed"])
            self.assertIn("EUD COM", report["error"])

    def test_audit_rejects_wrong_tcpm_current(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture, tree = self._ready(temporary)
            write(
                tree["sys_root"] / "class/power_supply/tcpm-source-psy-0-0000/current_now",
                "100000\n",
            )
            report = postboot_audit.audit(audit_runtime(fixture, tree))
            self.assertFalse(report["passed"])
            self.assertIn("TCPM", report["error"])

    def test_audit_rejects_wrong_mp2650_voltage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture, tree = self._ready(temporary)
            write(
                tree["sys_root"]
                / "class/power_supply/mp2650-input/constant_charge_voltage",
                "9000000\n",
            )
            report = postboot_audit.audit(audit_runtime(fixture, tree))
            self.assertFalse(report["passed"])
            self.assertIn("MP2650", report["error"])

    def test_audit_rejects_nonzero_protection_or_fault(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture, tree = self._ready(temporary)
            tree["status"]["sample"]["fault"] = 1
            report = postboot_audit.audit(audit_runtime(fixture, tree))
            self.assertFalse(report["passed"])
            self.assertIn("fault", report["error"])

    def test_audit_rejects_shadow_stale_or_manual_inhibit_sample(self) -> None:
        mutations = {
            "shadow": {"shadow": 1},
            "stale": {"age_ms": 999999},
            "manual_inhibit": {"desired_enable": 0},
        }
        for name, mutation in mutations.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                fixture, tree = self._ready(temporary)
                tree["status"]["sample"].update(mutation)
                report = postboot_audit.audit(audit_runtime(fixture, tree))
                self.assertFalse(report["passed"], report)
                self.assertIn("sample", report["error"])

    def test_audit_accepts_explicit_full_hold(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture, tree = self._ready(temporary)
            tree["status"]["sample"].update(
                {
                    "desired_enable": 0,
                    "logical_full": 1,
                    "hold_requested": 1,
                    "full_holding": 1,
                    "full_cause": 3,
                }
            )
            report = postboot_audit.audit(audit_runtime(fixture, tree))
            self.assertTrue(report["passed"], report)
            self.assertEqual(report["protection"]["sample_mode"], "full-hold")

    def test_transient_sysfs_enodata_is_retried(self) -> None:
        path = Path("synthetic-power-supply")
        calls = []

        def flaky_read(candidate, *args, **kwargs):
            if candidate == path and not calls:
                calls.append("enodata")
                raise OSError(errno.ENODATA, "No data available")
            self.assertEqual(candidate, path)
            return "500000\n"

        with mock.patch.object(Path, "read_text", flaky_read):
            self.assertEqual(postboot_audit._text(path), "500000")
        self.assertEqual(calls, ["enodata"])

    def test_audit_does_not_require_success_log_strings(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture, tree = self._ready(temporary)
            self.assertNotIn("fixed5V callbacks joined", tree["dmesg"])
            self.assertNotIn("adc", tree["dmesg"].lower())
            report = postboot_audit.audit(audit_runtime(fixture, tree))
            self.assertTrue(report["passed"], report)
            self.assertEqual(
                report["apsd_adc"]["adc_reader_evidence"],
                "direct_processed_PM8150B_ADC5_usb_in_v_div_16",
            )
            self.assertEqual(
                report["apsd_adc"]["adc_samples_uv"],
                [4511408, 4511408, 4511408],
            )

    def test_audit_accepts_measured_sdp_adc_window(self) -> None:
        for sample in (4511408, 4672304):
            with self.subTest(sample=sample), tempfile.TemporaryDirectory() as temporary:
                fixture, tree = self._ready(temporary)
                adc_input = (
                    tree["sys_root"]
                    / "bus/iio/devices/iio-device0/"
                    "in_voltage_usb_in_v_div_16_input"
                )
                adc_input.write_text(f"{sample}\n")
                report = postboot_audit.audit(audit_runtime(fixture, tree))
                self.assertTrue(report["passed"], report)
                self.assertEqual(report["apsd_adc"]["adc_samples_uv"], [sample] * 3)

    def test_audit_rejects_apsd_adc_outside_handoff_window(self) -> None:
        for sample in (4399999, 5500001):
            with self.subTest(sample=sample), tempfile.TemporaryDirectory() as temporary:
                fixture, tree = self._ready(temporary)
                adc_input = (
                    tree["sys_root"]
                    / "bus/iio/devices/iio-device0/"
                    "in_voltage_usb_in_v_div_16_input"
                )
                adc_input.write_text(f"{sample}\n")
                report = postboot_audit.audit(audit_runtime(fixture, tree))
                self.assertFalse(report["passed"])
                self.assertIn("APSD ADC/VBUS", report["error"])

    def test_audit_rejects_apsd_takeover_refusal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture, tree = self._ready(temporary)
            tree["dmesg"] += (
                "\n[9.0] qcom,pmic-typec c440000.spmi:pmic@2:typec@1500: "
                "full-PD APSD/QC takeover refused: -5"
            )
            report = postboot_audit.audit(audit_runtime(fixture, tree))
            self.assertFalse(report["passed"])
            self.assertIn("refused", report["error"])

    def test_audit_requires_explicit_apsd_handoff_property(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture, tree = self._ready(temporary)
            property_path = (
                tree["sys_root"]
                / "firmware/devicetree/base/soc@0/spmi@c440000/pmic@2/typec@1500/realme,apsd-handoff-trial"
            )
            property_path.unlink()
            report = postboot_audit.audit(audit_runtime(fixture, tree))
            self.assertFalse(report["passed"])
            self.assertIn("apsd-handoff-trial", report["error"])

    def test_audit_requires_typec_supply_dt_property(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture, tree = self._ready(temporary)
            property_path = (
                tree["sys_root"]
                / "firmware/devicetree/base/soc@0/geniqup@8c0000/i2c@884000/"
                "charger@5c/typec-supply"
            )
            property_path.unlink()
            report = postboot_audit.audit(audit_runtime(fixture, tree))
            self.assertFalse(report["passed"])
            self.assertIn("typec-supply", report["error"])

    def test_audit_requires_exact_usb_in_v_div_16_dt_label(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture, tree = self._ready(temporary)
            property_path = (
                tree["sys_root"]
                / "firmware/devicetree/base/soc@0/spmi@c440000/pmic@2/"
                "adc@3100/channel@8/label"
            )
            property_path.unlink()
            report = postboot_audit.audit(audit_runtime(fixture, tree))
            self.assertFalse(report["passed"])
            self.assertIn("usb_in_v_div_16", report["error"])
            property_path.write_bytes(b"usb_in_v_div_8\x00")
            report = postboot_audit.audit(audit_runtime(fixture, tree))
            self.assertFalse(report["passed"])
            self.assertIn("unexpected usb_in_v_div_16", report["error"])

    def test_audit_checks_apsd_property_presence_not_value(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture, tree = self._ready(temporary)
            property_path = (
                tree["sys_root"]
                / "firmware/devicetree/base/soc@0/spmi@c440000/pmic@2/typec@1500/realme,apsd-handoff-trial"
            )
            property_path.write_bytes(b"\x00\x00\x00\x00")
            report = postboot_audit.audit(audit_runtime(fixture, tree))
            self.assertTrue(report["passed"], report)

    def test_audit_rejects_new_taint_and_warning(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture, tree = self._ready(temporary)
            write(fixture["proc"] / "sys/kernel/tainted", "8192\n")
            report = postboot_audit.audit(audit_runtime(fixture, tree))
            self.assertFalse(report["passed"])
            self.assertIn("taint", report["error"])
            write(fixture["proc"] / "sys/kernel/tainted", "4096\n")
            tree["dmesg"] += "\n[9.0] WARNING: CPU: 0 PID: 1 at example.c:1"
            report = postboot_audit.audit(audit_runtime(fixture, tree))
            self.assertFalse(report["passed"])
            self.assertIn("warning", report["error"])

    def test_audit_ignores_debug_and_ramoops_word_substrings(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture, tree = self._ready(temporary)
            tree["dmesg"] += (
                "\n[0.000000] printk: debug: ignoring loglevel setting."
                "\n[0.055883] ramoops: using 0x400000@0xb7e00000, ecc: 0"
            )
            report = postboot_audit.audit(audit_runtime(fixture, tree))
            self.assertTrue(report["passed"], report)

    def test_ack_writes_boot_bound_token_after_readonly_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture, tree = self._ready(temporary)
            report = postboot_audit.audit(audit_runtime(fixture, tree))
            self.assertTrue(report["passed"], report)
            report_path = write(
                fixture["base"] / "audit-report.json",
                json.dumps(report, sort_keys=True) + "\n",
            )
            value = acknowledge_trial.issue(
                report_path,
                root=fixture["root"],
                manifest_path=fixture["target_manifest"],
                confirm_boot_id=NEW_BOOT_ID,
                boot_id_reader=lambda: NEW_BOOT_ID,
                require_root=False,
            )
            self.assertEqual(value["boot_id"], NEW_BOOT_ID)
            runtime = guard_runtime(fixture)
            self.assertTrue(
                trial_guard.accepted_token(runtime, trial_guard.load_manifest(runtime))
            )
            write(fixture["proc"] / "sys/kernel/random/boot_id", OTHER_BOOT_ID + "\n")
            other = guard_runtime(fixture)
            manifest = trial_guard.load_manifest(other)
            self.assertFalse(trial_guard.accepted_token(other, manifest))

    def test_ack_refuses_wrong_confirmation_or_failed_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture, tree = self._ready(temporary)
            report = postboot_audit.audit(audit_runtime(fixture, tree))
            report_path = write(
                fixture["base"] / "audit-report.json",
                json.dumps(report, sort_keys=True) + "\n",
            )
            with self.assertRaises(trial_common.TrialError):
                acknowledge_trial.issue(
                    report_path,
                    root=fixture["root"],
                    manifest_path=fixture["target_manifest"],
                    confirm_boot_id=OTHER_BOOT_ID,
                    boot_id_reader=lambda: NEW_BOOT_ID,
                    require_root=False,
                )
            report["passed"] = False
            write(report_path, json.dumps(report, sort_keys=True) + "\n")
            with self.assertRaises(trial_common.TrialError):
                acknowledge_trial.issue(
                    report_path,
                    root=fixture["root"],
                    manifest_path=fixture["target_manifest"],
                    confirm_boot_id=NEW_BOOT_ID,
                    boot_id_reader=lambda: NEW_BOOT_ID,
                    require_root=False,
                )


class AutoAuditTests(unittest.TestCase):
    def _ready(self, temporary: str) -> tuple[dict, dict]:
        fixture = make_fixture(Path(temporary))
        stage_fixture(fixture)
        new_boot(fixture)
        write_watchdog_state(fixture)
        runtime = guard_runtime(fixture)
        readback = trial_guard.verify_new_pair(
            runtime,
            trial_guard.load_manifest(runtime),
            json.loads((fixture["root"] / "stage.json").read_text()),
        )
        trial_common.atomic_write(
            fixture["root"] / "carrier-readback.json",
            (json.dumps(readback, sort_keys=True) + "\n").encode(),
        )
        tree = make_audit_tree(fixture)
        report = postboot_audit.audit(audit_runtime(fixture, tree))
        self.assertTrue(report["passed"], report)
        return fixture, report

    def test_autoaccept_writes_complete_report_and_bound_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture, report = self._ready(temporary)
            value = trial_autoaudit.run_until_accepted(
                root=fixture["root"],
                manifest_path=fixture["target_manifest"],
                deadline_boottime=200.0,
                max_attempts=1,
                boot_id_reader=lambda: NEW_BOOT_ID,
                boottime_reader=lambda: 11.0,
                sleeper=lambda _: None,
                audit_fn=lambda _runtime: report,
                runtime_factory=lambda: None,
                require_root=False,
            )
            self.assertTrue(value["accepted"])
            self.assertEqual(value["attempts"], 1)
            report_path = fixture["root"] / "auto-audit-report.json"
            auto_path = fixture["root"] / "auto-acceptance.json"
            accepted_path = fixture["root"] / "accepted.json"
            self.assertTrue(report_path.is_file())
            self.assertTrue(auto_path.is_file())
            self.assertTrue(accepted_path.is_file())
            accepted = json.loads(accepted_path.read_text())
            self.assertEqual(accepted["boot_id"], NEW_BOOT_ID)
            self.assertEqual(
                accepted["manifest_sha256"], sha(fixture["target_manifest"])
            )
            self.assertEqual(
                accepted["audit_report_sha256"], sha(report_path)
            )
            self.assertEqual(
                accepted["auto_acceptance_sha256"], sha(auto_path)
            )
            runtime = guard_runtime(fixture)
            self.assertTrue(
                trial_guard.accepted_token(
                    runtime, trial_guard.load_manifest(runtime)
                )
            )

    def test_failed_or_incomplete_report_never_writes_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture, report = self._ready(temporary)
            failed = dict(report)
            failed["passed"] = False
            value = trial_autoaudit.run_until_accepted(
                root=fixture["root"],
                manifest_path=fixture["target_manifest"],
                deadline_boottime=200.0,
                max_attempts=1,
                boot_id_reader=lambda: NEW_BOOT_ID,
                boottime_reader=lambda: 11.0,
                sleeper=lambda _: None,
                audit_fn=lambda _runtime: failed,
                runtime_factory=lambda: None,
                require_root=False,
            )
            self.assertFalse(value["accepted"])
            self.assertFalse((fixture["root"] / "auto-acceptance.json").exists())
            self.assertFalse((fixture["root"] / "accepted.json").exists())
            self.assertTrue((fixture["root"] / "auto-audit-last.json").exists())

            incomplete = dict(report)
            incomplete.pop("tcpm")
            with self.assertRaisesRegex(
                trial_common.TrialError, "audit report is incomplete"
            ):
                trial_autoaudit.record_acceptance(
                    incomplete,
                    root=fixture["root"],
                    manifest_path=fixture["target_manifest"],
                    boot_id_reader=lambda: NEW_BOOT_ID,
                    require_root=False,
                )
            self.assertFalse((fixture["root"] / "accepted.json").exists())

    def test_autoaccept_retries_after_audit_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture, report = self._ready(temporary)
            calls = []

            def audit_once(_runtime):
                calls.append("audit")
                if len(calls) == 1:
                    raise OSError("transient local audit error")
                return report

            value = trial_autoaudit.run_until_accepted(
                root=fixture["root"],
                manifest_path=fixture["target_manifest"],
                deadline_boottime=200.0,
                max_attempts=2,
                boot_id_reader=lambda: NEW_BOOT_ID,
                boottime_reader=lambda: 11.0,
                sleeper=lambda _: None,
                audit_fn=audit_once,
                runtime_factory=lambda: None,
                require_root=False,
            )
            self.assertTrue(value["accepted"])
            self.assertEqual(calls, ["audit", "audit"])
            self.assertEqual(value["attempts"], 2)
            failure = json.loads(
                (fixture["root"] / "auto-audit-last.json").read_text()
            )
            self.assertFalse(failure["passed"])
            self.assertIn("transient", failure["error"])

    def test_token_rejects_boot_manifest_and_report_hash_tamper(self) -> None:
        mutations = ("boot", "manifest", "report")
        for mutation in mutations:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                fixture, report = self._ready(temporary)
                trial_autoaudit.record_acceptance(
                    report,
                    root=fixture["root"],
                    manifest_path=fixture["target_manifest"],
                    boot_id_reader=lambda: NEW_BOOT_ID,
                    require_root=False,
                )
                accepted_path = fixture["root"] / "accepted.json"
                accepted = json.loads(accepted_path.read_text())
                if mutation == "boot":
                    accepted["boot_id"] = OTHER_BOOT_ID
                    write(
                        accepted_path,
                        json.dumps(accepted, indent=2, sort_keys=True) + "\n",
                    )
                elif mutation == "manifest":
                    accepted["manifest_sha256"] = "0" * 64
                    write(
                        accepted_path,
                        json.dumps(accepted, indent=2, sort_keys=True) + "\n",
                    )
                else:
                    report_path = fixture["root"] / "auto-audit-report.json"
                    changed = dict(report)
                    changed["version"] = "tampered"
                    write(report_path, trial_common.canonical_json_bytes(changed))
                runtime = guard_runtime(fixture)
                self.assertFalse(
                    trial_guard.accepted_token(
                        runtime, trial_guard.load_manifest(runtime)
                    )
                )

    def test_guard_rejects_installed_autoaudit_hash_tamper(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fixture(Path(temporary))
            stage_fixture(fixture)
            target = (
                fixture["target"]
                / trial_common.AUTOAUDIT_PATH.relative_to("/")
            )
            target.write_bytes(b"tampered-autoaudit\n")
            runtime = guard_runtime(fixture)
            with self.assertRaisesRegex(
                trial_common.TrialError, "installed file hash mismatch"
            ):
                trial_guard.verify_installed(
                    runtime, trial_guard.load_manifest(runtime)
                )

    def test_stage_rollback_restores_preexisting_audit_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fixture(Path(temporary))
            original_files = {}
            for path, payload in (
                (trial_common.POSTBOOT_AUDIT_PATH, b"# original postboot audit\n"),
                (trial_common.AUTOAUDIT_PATH, b"# original auto audit\n"),
            ):
                target = fixture["target"] / path.relative_to("/")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(payload)
                target.chmod(0o644 if path == trial_common.POSTBOOT_AUDIT_PATH else 0o755)
                original_files[path] = payload
            runtime = make_stage_runtime(fixture)
            original_install = trial_stage._install_module

            def fail_after_install(rt, manifest):
                original_install(rt, manifest)
                raise trial_common.TrialError("stop after device files installed")

            with mock.patch.object(
                trial_stage,
                "_install_module",
                side_effect=fail_after_install,
            ):
                with self.assertRaisesRegex(
                    trial_common.TrialError, "stop after device files installed"
                ):
                    trial_stage.stage(
                        runtime,
                        execute=True,
                        operator_serial=SERIAL,
                    )
            for path, payload in original_files.items():
                target = fixture["target"] / path.relative_to("/")
                self.assertEqual(target.read_bytes(), payload)
            self.assertFalse(
                (
                    fixture["target"]
                    / trial_common.COMMON_PATH.relative_to("/")
                ).exists()
            )
            failure = json.loads((fixture["root"] / "stage-failure.json").read_text())
            self.assertTrue(failure["restored_original_files"])

    def test_service_starts_autoaudit_after_managed_start_without_blocking(self) -> None:
        source = (TRIAL_DIR / "service/samurai-charging").read_text()
        self.assertIn("start_post()", source)
        self.assertIn("trial_autoaudit.py --daemon", source)
        self.assertIn("return 0", source)
        self.assertNotIn("start_pre() {\n    /usr/bin/python3 -B /usr/lib/samurai-charging/trial_autoaudit.py", source)


FAKE_FASTBOOT = r'''
param([Parameter(ValueFromRemainingArguments = $true)][string[]]$AllArgs)
$state = $env:FAKE_FASTBOOT_STATE
$argv = @($AllArgs)
if ($argv.Count -gt 2 -and $argv[0] -eq '-s') {
    if ($argv[1] -ne $env:FAKE_SERIAL) { exit 11 }
    $argv = @($argv[2..($argv.Count - 1)])
}
Add-Content -LiteralPath (Join-Path $state 'commands.log') -Value ($argv -join ' ')
$command = $argv[0]
if ($command -eq 'devices') {
    "$env:FAKE_SERIAL`tfastboot"
    exit 0
}
if ($command -eq 'getvar') {
    $name = $argv[1]
    if ($name -eq 'product') {
        '(bootloader) product: ' + $env:FAKE_PRODUCT
        exit 0
    }
    if ($name -eq 'partition-size:boot') {
        '(bootloader) partition-size:boot: 0x' + $env:FAKE_BOOT_SIZE_HEX
        exit 0
    }
    if ($name -eq 'partition-size:logdump') {
        '(bootloader) partition-size:logdump: 0x' + $env:FAKE_LOG_SIZE_HEX
        exit 0
    }
    exit 12
}
if ($command -eq 'fetch') {
    $partition = $argv[1]
    $out = $argv[2]
    if ($partition -eq 'boot' -and (Test-Path (Join-Path $state 'boot-flashed')) -and $env:FAKE_CORRUPT_BOOT -eq '1') {
        $bytes = [System.IO.File]::ReadAllBytes((Join-Path $state 'boot.img'))
        $bytes[0] = $bytes[0] -bxor 0xff
        [System.IO.File]::WriteAllBytes($out, $bytes)
        Remove-Item -LiteralPath (Join-Path $state 'boot-flashed')
        exit 0
    }
    Copy-Item -LiteralPath (Join-Path $state ($partition + '.img')) -Destination $out
    exit 0
}
if ($command -eq 'flash') {
    $partition = $argv[1]
    if ($partition -eq 'boot' -and $env:FAKE_FAIL_BOOT -eq '1' -and $argv[2].EndsWith('new-boot.img')) { exit 21 }
    if ($partition -eq 'logdump' -and $env:FAKE_FAIL_LOGDUMP -eq '1') { exit 22 }
    Copy-Item -LiteralPath $argv[2] -Destination (Join-Path $state ($partition + '.img'))
    if ($partition -eq 'boot' -and $argv[2].EndsWith('new-boot.img')) {
        New-Item -ItemType File -Force -Path (Join-Path $state 'boot-flashed') | Out-Null
    }
    exit 0
}
if ($command -eq 'reboot') {
    Add-Content -LiteralPath (Join-Path $state 'reboot.log') -Value 'reboot'
    exit 0
}
exit 13
'''


def make_fastboot_fixture(base: Path, *, host_fetch_unavailable: bool = False) -> dict:
    fixture = make_fixture(base)
    image_path = write(base / "images/new-image", blob("new-image", 128))
    fat_receipt_path = write(
        base / "images/fat-receipt.json",
        json.dumps(
            {
                "passed": True,
                "Image_readback_exact": True,
                "fsck_readonly_passed": True,
                "only_Image_file_changed": True,
                "Image507_R2_sha256": sha(image_path),
                "Image507_R2": {
                    "sha256": sha(image_path),
                    "bytes": image_path.stat().st_size,
                },
                "logdump_sha256": sha(fixture["new_paths"]["logdump"]),
                "logdump_bytes": fixture["new_paths"]["logdump"].stat().st_size,
                "candidate": {
                    "sha256": sha(fixture["new_paths"]["logdump"]),
                    "bytes": fixture["new_paths"]["logdump"].stat().st_size,
                },
                "rollback": {
                    "sha256": sha(fixture["old_paths"]["logdump"]),
                    "bytes": fixture["old_paths"]["logdump"].stat().st_size,
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )
    fixture["manifest"]["image"] = {
        "path": str(image_path),
        "sha256": sha(image_path),
        "bytes": image_path.stat().st_size,
        "fat_receipt_path": str(fat_receipt_path),
        "fat_receipt_sha256": sha(fat_receipt_path),
    }
    fixture["manifest"]["fastboot"]["host_fetch_unavailable"] = host_fetch_unavailable
    write(
        fixture["manifest_path"],
        json.dumps(fixture["manifest"], indent=2, sort_keys=True) + "\n",
    )
    state = base / "fastboot-state"
    state.mkdir()
    shutil.copy2(fixture["old_paths"]["boot"], state / "boot.img")
    shutil.copy2(fixture["old_paths"]["logdump"], state / "logdump.img")
    fake = write(base / "fake-fastboot.ps1", FAKE_FASTBOOT)
    manifest = fixture["manifest"]
    receipt = {
        "schema": 1,
        "trial_id": trial_common.TRIAL_ID,
        "passed": True,
        "stage_execute": True,
        "boot_id": OLD_BOOT_ID,
        "version_pin": trial_common.VERSION,
        "watch_seconds": trial_common.WATCH_SECONDS,
        "serial": SERIAL,
        "serial_source": "operator_cli",
        "guard_installed": True,
        "device_files_backed_up": True,
        "original_service_installed": True,
        "module_installed": True,
        "main_manifest_patched": True,
        "old_carriers_backed_up": True,
        "partition_identity_recorded": True,
        "partition_identity": fixture["identities"],
        "old_carrier_sha256": {
            name: manifest["carriers"][name]["old"] for name in SMALL_BYTES
        },
        "manifest_sha256": sha(fixture["manifest_path"]),
        "original_main_manifest": {
            "sha256": manifest["main_manifest"]["old_sha256"],
        },
        "original_module": {
            "name": manifest["kernel_module"]["name"],
            "target": manifest["kernel_module"]["target"],
            "sha256": manifest["kernel_module"]["old_sha256"],
            "bytes": manifest["kernel_module"]["old_bytes"],
        },
        "main_manifest_patch": {
            "target": manifest["main_manifest"]["target"],
            "old_sha256": manifest["main_manifest"]["old_sha256"],
            "new_sha256": "f" * 64,
            "service_target": manifest["main_manifest"]["service_target"],
            "service_sha256": manifest["device_files"][
                trial_common.SERVICE_PATH.as_posix()
            ]["sha256"],
            "device_files_sha256": {
                target: row["sha256"]
                for target, row in manifest["device_files"].items()
            },
            "module_name": manifest["kernel_module"]["name"],
            "module_target": manifest["kernel_module"]["target"],
            "module_old_sha256": manifest["kernel_module"]["old_sha256"],
            "module_new_sha256": manifest["kernel_module"]["new_sha256"],
        },
        "installed_file_sha256": {
            **{
                target: row["sha256"]
                for target, row in manifest["device_files"].items()
            },
            manifest["kernel_module"]["target"]: manifest["kernel_module"][
                "new_sha256"
            ],
            manifest["main_manifest"]["target"]: "f" * 64,
        },
        "original_device_files": {
            target: {
                "target": target,
                "state": "missing",
                "sha256": None,
                "bytes": None,
                "mode": None,
                "uid": None,
                "gid": None,
                "backup": None,
            }
            for target in manifest["device_files"]
            if target != trial_common.SERVICE_PATH.as_posix()
        },
        "new_carrier_written": False,
        "reboot_bootloader_requested": True,
        "restart_method": "restart2_syscall_142",
        "host_fetch_unavailable": host_fetch_unavailable,
        "restart2": {
            "syscall": 142,
            "magic1": 0xFEE1DEAD,
            "magic2": 672274793,
            "command": "bootloader",
            "command_value": 0xA1B2C3D4,
            "attempt_count": 1,
            "retry": False,
        },
    }
    receipt_path = write(
        base / "stage-receipt.json",
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
    )
    return {
        **fixture,
        "state": state,
        "fake": fake,
        "image_path": image_path,
        "fat_receipt_path": fat_receipt_path,
        "receipt_path": receipt_path,
        "commands_log": state / "commands.log",
        "reboot_log": state / "reboot.log",
    }


def run_fastboot_operator(
    fixture: dict,
    work: Path,
    *,
    execute: bool = True,
    no_fetch: bool = False,
    env_extra: dict | None = None,
) -> tuple[subprocess.CompletedProcess, dict]:
    pwsh = shutil.which("pwsh")
    if not pwsh:
        raise unittest.SkipTest("pwsh is required for host operator controls")
    report = work / "operator-report.json"
    env = os.environ.copy()
    env.update(
        {
            "FAKE_FASTBOOT_STATE": str(fixture["state"]),
            "FAKE_SERIAL": SERIAL,
            "FAKE_PRODUCT": "msmnile",
            "FAKE_BOOT_SIZE_HEX": f"{SMALL_BYTES['boot']:x}",
            "FAKE_LOG_SIZE_HEX": f"{SMALL_BYTES['logdump']:x}",
        }
    )
    env.update(env_extra or {})
    args = [
        pwsh,
        "-NoProfile",
        "-File",
        str(TRIAL_DIR / "fastboot_operator.ps1"),
        "-FastbootPath",
        str(fixture["fake"]),
        "-StageReceipt",
        str(fixture["receipt_path"]),
        "-ManifestPath",
        str(fixture["manifest_path"]),
        "-WorkDirectory",
        str(work),
        "-ReportPath",
        str(report),
    ]
    if execute:
        args.append("-Execute")
    if no_fetch:
        args.append("-NoFetch")
    result = subprocess.run(args, capture_output=True, text=True, env=env, timeout=120)
    value = json.loads(report.read_text())
    return result, value


class FastbootOperatorTests(unittest.TestCase):
    def test_local_validation_does_not_touch_fastboot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fastboot_fixture(Path(temporary))
            work = fixture["base"] / "work"
            result, report = run_fastboot_operator(fixture, work, execute=False)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertEqual(report["outcome"], "local_validation_only")
            self.assertFalse(report["device_touched"])
            self.assertFalse(fixture["commands_log"].exists())

    def test_success_flashes_logdump_then_boot_and_reboots_once(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fastboot_fixture(Path(temporary))
            work = fixture["base"] / "work"
            result, report = run_fastboot_operator(fixture, work)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertTrue(report["passed"])
            self.assertEqual(report["outcome"], "new_pair_verified_and_rebooted")
            self.assertEqual(report["reboot_count"], 1)
            self.assertEqual(
                report["pinned_inputs"]["dtb"], sha(fixture["dtb_path"])
            )
            self.assertEqual(
                report["pinned_inputs"]["boot_receipt"],
                sha(fixture["boot_receipt_path"]),
            )
            self.assertTrue(
                report["pinned_inputs"]["dtb_embedded_in_boot_not_flashed"]
            )
            commands = fixture["commands_log"].read_text().splitlines()
            flashes = [line for line in commands if line.startswith("flash ")]
            self.assertEqual(len(flashes), 2)
            self.assertTrue(flashes[0].startswith("flash logdump "))
            self.assertTrue(flashes[1].startswith("flash boot "))
            self.assertEqual(fixture["reboot_log"].read_text().splitlines(), ["reboot"])
            for forbidden in ("erase", "format", "unlock", "set_active", "pd5v", "9v"):
                self.assertNotIn(forbidden, "\n".join(commands).lower())

    def test_no_fetch_success_uses_guard_readback_and_one_reboot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fastboot_fixture(
                Path(temporary), host_fetch_unavailable=True
            )
            result, report = run_fastboot_operator(
                fixture, fixture["base"] / "work", no_fetch=True
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertTrue(report["passed"])
            self.assertTrue(report["host_fetch_unavailable"])
            self.assertFalse(report["host_readback_verified"])
            self.assertTrue(report["guard_carrier_readback_required"])
            self.assertEqual(
                report["outcome"],
                "new_pair_flashed_no_host_readback_guard_readback_required",
            )
            commands = fixture["commands_log"].read_text().splitlines()
            self.assertFalse(any(line.startswith("fetch ") for line in commands))
            flashes = [line for line in commands if line.startswith("flash ")]
            self.assertEqual(
                [line.split()[1] for line in flashes], ["logdump", "boot"]
            )
            self.assertEqual(fixture["reboot_log"].read_text().splitlines(), ["reboot"])

    def test_no_fetch_requires_receipt_host_fetch_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fastboot_fixture(Path(temporary))
            result, report = run_fastboot_operator(
                fixture, fixture["base"] / "work", no_fetch=True
            )
            self.assertEqual(result.returncode, 3)
            self.assertIn("host_fetch_unavailable=true", report["error"])
            self.assertFalse(fixture["commands_log"].exists())

    def test_fetch_mode_rejects_receipt_declaring_fetch_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fastboot_fixture(
                Path(temporary), host_fetch_unavailable=True
            )
            result, report = run_fastboot_operator(
                fixture, fixture["base"] / "work"
            )
            self.assertEqual(result.returncode, 3)
            self.assertIn("pass -NoFetch", report["error"])
            self.assertFalse(fixture["commands_log"].exists())

    def test_no_fetch_boot_failure_restores_old_pair_without_readback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fastboot_fixture(
                Path(temporary), host_fetch_unavailable=True
            )
            result, report = run_fastboot_operator(
                fixture,
                fixture["base"] / "work",
                no_fetch=True,
                env_extra={"FAKE_FAIL_BOOT": "1"},
            )
            self.assertEqual(result.returncode, 3, result.stderr + result.stdout)
            self.assertEqual(
                report["outcome"],
                "old_pair_restored_without_host_readback_and_rebooted",
            )
            commands = fixture["commands_log"].read_text().splitlines()
            self.assertFalse(any(line.startswith("fetch ") for line in commands))
            flashes = [line for line in commands if line.startswith("flash ")]
            self.assertEqual(
                [line.split()[1] for line in flashes],
                ["logdump", "boot", "boot", "logdump"],
            )
            self.assertEqual(fixture["reboot_log"].read_text().splitlines(), ["reboot"])

    def test_boot_flash_failure_restores_old_pair_and_reboots_once(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fastboot_fixture(Path(temporary))
            work = fixture["base"] / "work"
            result, report = run_fastboot_operator(
                fixture, work, env_extra={"FAKE_FAIL_BOOT": "1"}
            )
            self.assertEqual(result.returncode, 3, result.stderr + result.stdout)
            self.assertFalse(report["passed"])
            self.assertEqual(report["outcome"], "old_pair_restored_and_rebooted")
            commands = fixture["commands_log"].read_text().splitlines()
            flashes = [line for line in commands if line.startswith("flash ")]
            self.assertEqual(
                [line.split()[1] for line in flashes],
                ["logdump", "boot", "boot", "logdump"],
            )
            self.assertEqual(fixture["reboot_log"].read_text().splitlines(), ["reboot"])
            self.assertEqual(
                (fixture["state"] / "boot.img").read_bytes(),
                fixture["old_paths"]["boot"].read_bytes(),
            )
            self.assertEqual(
                (fixture["state"] / "logdump.img").read_bytes(),
                fixture["old_paths"]["logdump"].read_bytes(),
            )

    def test_readback_mismatch_restores_old_pair_without_new_retry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fastboot_fixture(Path(temporary))
            work = fixture["base"] / "work"
            result, report = run_fastboot_operator(
                fixture, work, env_extra={"FAKE_CORRUPT_BOOT": "1"}
            )
            self.assertEqual(result.returncode, 3, result.stderr + result.stdout)
            self.assertEqual(report["outcome"], "old_pair_restored_and_rebooted")
            flashes = [
                line for line in fixture["commands_log"].read_text().splitlines() if line.startswith("flash ")
            ]
            self.assertEqual(
                [line.split()[1] for line in flashes],
                ["logdump", "boot", "boot", "logdump"],
            )
            self.assertEqual(fixture["reboot_log"].read_text().splitlines(), ["reboot"])

    def test_preflight_current_pair_mismatch_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fastboot_fixture(Path(temporary))
            shutil.copy2(fixture["new_paths"]["logdump"], fixture["state"] / "logdump.img")
            work = fixture["base"] / "work"
            result, report = run_fastboot_operator(fixture, work)
            self.assertEqual(result.returncode, 3, result.stderr + result.stdout)
            self.assertFalse(report["writes_attempted"])
            commands = fixture["commands_log"].read_text().splitlines()
            self.assertFalse(any(line.startswith("flash ") for line in commands))
            self.assertFalse(fixture["reboot_log"].exists())

    def test_wrong_product_or_partition_size_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fastboot_fixture(Path(temporary))
            result, report = run_fastboot_operator(
                fixture,
                fixture["base"] / "work",
                env_extra={"FAKE_PRODUCT": "other"},
            )
            self.assertEqual(result.returncode, 3)
            self.assertFalse(report["writes_attempted"])
            self.assertFalse(
                any(line.startswith("flash ") for line in fixture["commands_log"].read_text().splitlines())
            )
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fastboot_fixture(Path(temporary))
            result, report = run_fastboot_operator(
                fixture,
                fixture["base"] / "work",
                env_extra={"FAKE_BOOT_SIZE_HEX": "61"},
            )
            self.assertEqual(result.returncode, 3)
            self.assertFalse(report["writes_attempted"])

    def test_dtb_tamper_prevents_fastboot_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fastboot_fixture(Path(temporary))
            fixture["dtb_path"].write_bytes(b"X" * fixture["dtb_path"].stat().st_size)
            result, report = run_fastboot_operator(
                fixture, fixture["base"] / "work"
            )
            self.assertEqual(result.returncode, 3)
            self.assertIn("DTB hash mismatch", report["error"])
            self.assertFalse(fixture["commands_log"].exists())

    def test_module_tamper_prevents_fastboot_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fastboot_fixture(Path(temporary))
            module_path = fixture["package"] / trial_common.MODULE_SOURCE
            module_path.write_bytes(b"X" * module_path.stat().st_size)
            result, report = run_fastboot_operator(
                fixture, fixture["base"] / "work"
            )
            self.assertEqual(result.returncode, 3)
            self.assertIn("replacement kernel module hash mismatch", report["error"])
            self.assertFalse(fixture["commands_log"].exists())

    def test_boot_receipt_tamper_prevents_fastboot_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fastboot_fixture(Path(temporary))
            receipt = json.loads(fixture["boot_receipt_path"].read_text())
            receipt["native_DTB_sha256"] = "0" * 64
            write(
                fixture["boot_receipt_path"],
                json.dumps(receipt, sort_keys=True) + "\n",
            )
            result, report = run_fastboot_operator(
                fixture, fixture["base"] / "work"
            )
            self.assertEqual(result.returncode, 3)
            self.assertIn("boot package receipt hash mismatch", report["error"])
            self.assertFalse(fixture["commands_log"].exists())

    def test_fat_receipt_tamper_prevents_fastboot_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fastboot_fixture(Path(temporary))
            receipt = json.loads(fixture["fat_receipt_path"].read_text())
            receipt["Image507_R2_sha256"] = "0" * 64
            write(
                fixture["fat_receipt_path"],
                json.dumps(receipt, sort_keys=True) + "\n",
            )
            result, report = run_fastboot_operator(
                fixture, fixture["base"] / "work"
            )
            self.assertEqual(result.returncode, 3)
            self.assertIn("FAT receipt hash mismatch", report["error"])
            self.assertFalse(fixture["commands_log"].exists())

    def test_fastboot_rejects_a_different_real_device_serial(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fastboot_fixture(Path(temporary))
            result, report = run_fastboot_operator(
                fixture,
                fixture["base"] / "work",
                env_extra={"FAKE_SERIAL": "deadbeef"},
            )
            self.assertEqual(result.returncode, 3)
            self.assertFalse(report["writes_attempted"])
            self.assertIn("unexpected device serial", report["error"])
            self.assertFalse(
                any(
                    line.startswith("flash ")
                    for line in fixture["commands_log"].read_text().splitlines()
                )
            )

    def test_missing_stage_receipt_never_invokes_fastboot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fastboot_fixture(Path(temporary))
            fixture["receipt_path"].unlink()
            result, report = run_fastboot_operator(fixture, fixture["base"] / "work")
            self.assertEqual(result.returncode, 3)
            self.assertEqual(report["outcome"], "not_started")
            self.assertFalse(fixture["commands_log"].exists())

    def test_main_manifest_patch_receipt_mismatch_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fastboot_fixture(Path(temporary))
            receipt = json.loads(fixture["receipt_path"].read_text())
            receipt["main_manifest_patch"]["new_sha256"] = "e" * 64
            write(
                fixture["receipt_path"],
                json.dumps(receipt, indent=2, sort_keys=True) + "\n",
            )
            result, report = run_fastboot_operator(
                fixture, fixture["base"] / "work"
            )
            self.assertEqual(result.returncode, 3)
            self.assertIn("main manifest patch hash", report["error"])
            self.assertFalse(fixture["commands_log"].exists())

    def test_module_patch_receipt_mismatch_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fastboot_fixture(Path(temporary))
            receipt = json.loads(fixture["receipt_path"].read_text())
            receipt["main_manifest_patch"]["module_new_sha256"] = "e" * 64
            write(
                fixture["receipt_path"],
                json.dumps(receipt, indent=2, sort_keys=True) + "\n",
            )
            result, report = run_fastboot_operator(
                fixture, fixture["base"] / "work"
            )
            self.assertEqual(result.returncode, 3)
            self.assertIn("main manifest patch metadata mismatch", report["error"])
            self.assertFalse(fixture["commands_log"].exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
