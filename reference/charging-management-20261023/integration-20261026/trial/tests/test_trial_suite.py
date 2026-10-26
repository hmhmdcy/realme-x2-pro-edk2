from __future__ import annotations

import ctypes
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


def blob(label: str, size: int) -> bytes:
    seed = hashlib.sha256(label.encode()).digest()
    return (seed * ((size + len(seed) - 1) // len(seed)))[:size]


def snapshot(root: Path) -> dict[str, str]:
    result = {}
    for path in sorted(Path(root).rglob("*")):
        if path.is_file():
            result[str(path.relative_to(root))] = sha(path)
    return result


def build_manifest(package: Path, old_paths: dict[str, Path], new_paths: dict[str, Path]) -> dict:
    device_files = {
        str(trial_common.COMMON_PATH): {
            "source": "trial_common.py",
            "target": str(trial_common.COMMON_PATH),
            "mode": 0o644,
            "sha256": sha(package / "trial_common.py"),
        },
        str(trial_common.GUARD_PATH): {
            "source": "trial_guard.py",
            "target": str(trial_common.GUARD_PATH),
            "mode": 0o755,
            "sha256": sha(package / "trial_guard.py"),
        },
        str(trial_common.SERVICE_PATH): {
            "source": "service/samurai-charging",
            "target": str(trial_common.SERVICE_PATH),
            "mode": 0o755,
            "sha256": sha(package / "service/samurai-charging"),
        },
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
        },
        "device_files": device_files,
        "carriers": carriers,
    }


def package_copy(destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copy2(TRIAL_DIR / "trial_common.py", destination / "trial_common.py")
    shutil.copy2(TRIAL_DIR / "trial_guard.py", destination / "trial_guard.py")
    (destination / "service").mkdir(exist_ok=True)
    shutil.copy2(
        TRIAL_DIR / "service/samurai-charging",
        destination / "service/samurai-charging",
    )
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
    devices = {
        "boot": write(base / "devices/boot.img", old_paths["boot"].read_bytes()),
        "logdump": write(base / "devices/logdump.img", old_paths["logdump"].read_bytes()),
    }
    manifest = build_manifest(package, old_paths, new_paths)
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
        "devices": devices,
        "identities": identities,
        "root": base / "evidence",
        "original_service": original_service,
        "original_service_bytes": original_service.read_bytes(),
        "original_service_sha256": sha(original_service),
    }


def stage_fixture(fixture: dict, *, reboot_calls: list | None = None) -> dict:
    calls = reboot_calls if reboot_calls is not None else []
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


def make_audit_tree(fixture: dict) -> dict:
    sys_root = fixture["base"] / "sys"
    write(sys_root / "class/net/usb0/device/driver/name", "cdc_ncm\n")
    typec_binding = sys_root / "test-typec-binding"
    write(typec_binding / "marker", "bound\n")
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
    write(ps / "mp2650-input/input_current_limit", "500000\n")
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
            "valid": 1,
            "online": 1,
            "protection_ok": 1,
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
        strict_carrier_pins=False,
        partition_bytes=SMALL_BYTES,
        boottime=lambda: 11.0,
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
            )
            receipt = trial_stage.stage(
                runtime, execute=False, operator_serial=SERIAL
            )
            self.assertFalse(receipt["guard_installed"])
            self.assertFalse(receipt["old_carriers_backed_up"])
            self.assertEqual(receipt["serial_source"], "operator_cli")
            self.assertFalse((fixture["root"] / "original/samurai-charging").exists())
            self.assertEqual(fixture["original_service"].read_text(), "#!/sbin/openrc-run\n# original service\n")
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
            )
            with self.assertRaisesRegex(
                trial_common.TrialError, "rerun with --serial 62bc28a1"
            ):
                trial_stage.stage(runtime, execute=False)

    def test_guard_accepts_only_a_token_for_the_current_boot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fixture(Path(temporary))
            stage_fixture(fixture)
            new_boot(fixture)
            reboot_calls = []
            runtime = guard_runtime(fixture, reboot_calls=reboot_calls)
            token = {
                "schema": 1,
                "trial_id": trial_common.TRIAL_ID,
                "token": trial_common.TOKEN,
                "boot_id": NEW_BOOT_ID,
                "manifest_sha256": sha(fixture["target_manifest"]),
                "audit_report_sha256": "a" * 64,
            }
            trial_common.atomic_write(
                fixture["root"] / "accepted.json",
                (json.dumps(token) + "\n").encode(),
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


class PostbootAuditTests(unittest.TestCase):
    def _ready(self, temporary: str) -> tuple[dict, dict]:
        fixture = make_fixture(Path(temporary))
        stage_fixture(fixture)
        new_boot(fixture)
        write_watchdog_state(fixture)
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

    def test_audit_rejects_wrong_version(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture, tree = self._ready(temporary)
            report = postboot_audit.audit(
                audit_runtime(fixture, tree, version="#510 SMP PREEMPT")
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

    def test_audit_rejects_missing_ncm_binding(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture, tree = self._ready(temporary)
            write(tree["sys_root"] / "class/net/usb0/device/driver/name", "rndis_host\n")
            report = postboot_audit.audit(audit_runtime(fixture, tree))
            self.assertFalse(report["passed"])
            self.assertIn("cdc_ncm", report["error"])

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

    def test_audit_does_not_require_success_log_strings(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture, tree = self._ready(temporary)
            self.assertNotIn("fixed5V callbacks joined", tree["dmesg"])
            self.assertNotIn("adc", tree["dmesg"].lower())
            report = postboot_audit.audit(audit_runtime(fixture, tree))
            self.assertTrue(report["passed"], report)
            self.assertEqual(
                report["apsd_adc"]["adc_reader_evidence"],
                "inferred_from_successful_full_PD_profile_probe",
            )

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


def make_fastboot_fixture(base: Path) -> dict:
    fixture = make_fixture(base)
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
        "original_service_installed": True,
        "old_carriers_backed_up": True,
        "partition_identity_recorded": True,
        "partition_identity": fixture["identities"],
        "old_carrier_sha256": {
            name: manifest["carriers"][name]["old"] for name in SMALL_BYTES
        },
        "manifest_sha256": sha(fixture["manifest_path"]),
        "installed_file_sha256": {
            target: row["sha256"] for target, row in manifest["device_files"].items()
        },
        "new_carrier_written": False,
        "reboot_bootloader_requested": True,
        "restart_method": "restart2_syscall_142",
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
        "receipt_path": receipt_path,
        "commands_log": state / "commands.log",
        "reboot_log": state / "reboot.log",
    }


def run_fastboot_operator(
    fixture: dict,
    work: Path,
    *,
    execute: bool = True,
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
            commands = fixture["commands_log"].read_text().splitlines()
            flashes = [line for line in commands if line.startswith("flash ")]
            self.assertEqual(len(flashes), 2)
            self.assertTrue(flashes[0].startswith("flash logdump "))
            self.assertTrue(flashes[1].startswith("flash boot "))
            self.assertEqual(fixture["reboot_log"].read_text().splitlines(), ["reboot"])
            for forbidden in ("erase", "format", "unlock", "set_active", "pd5v", "9v"):
                self.assertNotIn(forbidden, "\n".join(commands).lower())

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
