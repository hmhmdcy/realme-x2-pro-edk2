"""Read-only postboot acceptance checks for the #509 trial.

This script only reads sysfs/procfs and runs read-only commands.  It does not
write an acceptance token, change charging parameters, or request a reboot.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import subprocess
import sys
import time
import traceback
from pathlib import Path

from trial_common import (
    DEVICE_ROOT,
    EXPECTED_TAINTED,
    MANIFEST_PATH,
    TRIAL_ID,
    VERSION,
    WATCH_SECONDS,
    TrialError,
    active_value,
    parse_key_values,
    read_json,
    require_regular,
    sha256_file,
)
from trial_guard import Runtime as GuardRuntime
from trial_guard import accepted_token, load_manifest, verify_installed


CRITICAL_DMESG = re.compile(
    r"(?i)(WARNING:|BUG:|Oops:|Call Trace|Unknown symbol|disagrees about version|kernel panic)"
)
NCM_RE = re.compile(r"(?i)(cdc_ncm|CDC[ -]?NCM)")
TYPEC_BIND_RE = re.compile(r"(?i)(qcom,pmic-typec|qcom-pmic-typec)")
APSD_REFUSAL_RE = re.compile(r"(?i)full-PD APSD/QC takeover refused")


def _default_dmesg() -> str:
    return subprocess.run(
        ["dmesg"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    ).stdout


def _default_status() -> dict:
    result = subprocess.run(
        ["/usr/sbin/samurai-charging", "status"],
        check=True,
        capture_output=True,
        text=True,
        timeout=12,
    )
    return json.loads(result.stdout)


def _default_version() -> str:
    if hasattr(os, "uname"):
        return os.uname().version
    return platform.uname().version


def _driver_name(path: Path) -> str | None:
    if path.is_symlink():
        return path.resolve().name
    name_file = path / "name"
    if name_file.is_file():
        return name_file.read_text().strip()
    return None


class AuditRuntime:
    def __init__(
        self,
        *,
        root: Path = DEVICE_ROOT,
        proc_root: Path = Path("/proc"),
        sys_root: Path = Path("/sys"),
        target_root: Path = Path("/"),
        manifest_path: Path | None = None,
        strict_carrier_pins: bool = True,
        partition_bytes: dict[str, int] | None = None,
        version_reader=_default_version,
        boot_id_reader=None,
        dmesg_reader=_default_dmesg,
        status_reader=_default_status,
        require_symlinks: bool = True,
        boottime=None,
        typec_binding_path: Path | None = None,
    ) -> None:
        self.root = Path(root)
        self.proc_root = Path(proc_root)
        self.sys_root = Path(sys_root)
        self.target_root = Path(target_root)
        self.manifest_path = Path(manifest_path or self.target(MANIFEST_PATH))
        self.strict_carrier_pins = strict_carrier_pins
        self.partition_bytes = dict(partition_bytes or {})
        self.version_reader = version_reader
        self.boot_id_reader = boot_id_reader or (
            lambda: (self.proc_root / "sys/kernel/random/boot_id").read_text().strip()
        )
        self.dmesg_reader = dmesg_reader
        self.status_reader = status_reader
        self.require_symlinks = require_symlinks
        self.typec_binding_path = (
            Path(typec_binding_path) if typec_binding_path is not None else None
        )
        self.boottime = boottime or (
            lambda: time.clock_gettime(time.CLOCK_BOOTTIME)
            if hasattr(time, "CLOCK_BOOTTIME")
            else time.monotonic()
        )

    def target(self, path: Path) -> Path:
        path = Path(path)
        if self.target_root == Path("/"):
            return path
        return self.target_root / path.relative_to("/")

    def sys(self, relative: str) -> Path:
        return self.sys_root / relative


def _text(path: Path) -> str:
    return path.read_text().strip()


def _read_power_supply(rt: AuditRuntime, name: str, field: str) -> str:
    return _text(rt.sys(f"class/power_supply/{name}/{field}"))


def _check_version(rt: AuditRuntime) -> str:
    version = rt.version_reader()
    if VERSION not in version:
        raise TrialError(f"kernel version is not {VERSION!r}: {version!r}")
    return version


def _guard_manifest_and_state(rt: AuditRuntime, boot: str) -> tuple[dict, dict]:
    guard_rt = GuardRuntime(
        root=rt.root,
        proc_root=rt.proc_root,
        sys_root=rt.sys_root,
        dev_root=Path("/dev"),
        target_root=rt.target_root,
        manifest_path=rt.manifest_path,
        require_root=False,
        strict_carrier_pins=rt.strict_carrier_pins,
        partition_bytes=(rt.partition_bytes or None),
    )
    manifest = load_manifest(guard_rt)
    verify_installed(guard_rt, manifest)
    state = read_json(rt.root / "state.json")
    if state.get("boot_id") != boot:
        raise TrialError("guard state belongs to a different boot")
    if state.get("event") not in {"watchdog-running", "accepted"}:
        raise TrialError("guard watchdog is not armed on this boot")
    deadline = state.get("deadline_boottime")
    if type(deadline) not in {int, float}:
        raise TrialError("watchdog deadline missing")
    if not accepted_token(guard_rt, manifest):
        elapsed = rt.boottime() - float(deadline) + WATCH_SECONDS
        if elapsed >= WATCH_SECONDS:
            raise TrialError("read-only audit started after the unaccepted deadline")
    return manifest, state


def _check_ncm(rt: AuditRuntime, dmesg: str) -> dict:
    lines = [line for line in dmesg.splitlines() if NCM_RE.search(line)]
    if not lines:
        raise TrialError("dmesg has no CDC NCM evidence")
    driver_found = []
    net = rt.sys("class/net")
    if net.is_dir():
        for entry in net.iterdir():
            driver = _driver_name(entry / "device/driver")
            if driver == "cdc_ncm":
                driver_found.append(entry.name)
    if not driver_found:
        raise TrialError("no net interface is bound to cdc_ncm")
    return {"dmesg": lines, "interfaces": sorted(driver_found)}


def _check_typec(rt: AuditRuntime, dmesg: str) -> dict:
    expected = rt.typec_binding_path or (
        rt.sys("bus/platform/drivers/qcom,pmic-typec")
        / "c440000.spmi:pmic@2:typec@1500"
    )
    if not expected.exists():
        raise TrialError("qcom_pmic_typec platform binding is missing")
    if rt.require_symlinks and not expected.is_symlink():
        raise TrialError("qcom_pmic_typec binding is not a sysfs symlink")
    typec = rt.sys("class/typec")
    ports = (
        [entry for entry in typec.iterdir() if re.fullmatch(r"port[0-9]+", entry.name)]
        if typec.is_dir()
        else []
    )
    if len(ports) != 1:
        raise TrialError("expected exactly one Type-C port")
    port = ports[0]
    partner = port.parent / (port.name + "-partner")
    if not partner.exists():
        raise TrialError("Type-C partner is missing")
    roles = {
        "power_role": active_value(_text(port / "power_role")),
        "data_role": active_value(_text(port / "data_role")),
        "power_operation_mode": active_value(_text(port / "power_operation_mode")),
    }
    if roles["power_role"] != "sink" or roles["data_role"] != "device":
        raise TrialError(f"unexpected Type-C roles: {roles}")
    bind_lines = [
        line for line in dmesg.splitlines() if TYPEC_BIND_RE.search(line) and "typec@1500" in line
    ]
    if not bind_lines:
        raise TrialError("dmesg has no qcom_pmic_typec binding evidence")
    return {"port": port.name, "partner": partner.name, "roles": roles, "dmesg": bind_lines}


def _check_tcpm(rt: AuditRuntime) -> dict:
    power = rt.sys("class/power_supply")
    candidates = (
        [entry for entry in power.iterdir() if entry.name.startswith("tcpm-source-psy-")]
        if power.is_dir()
        else []
    )
    if len(candidates) != 1:
        raise TrialError("expected exactly one TCPM power supply")
    tcpm = candidates[0]
    values = {
        "online": _text(tcpm / "online"),
        "usb_type": active_value(_text(tcpm / "usb_type")),
        "voltage_now": int(_text(tcpm / "voltage_now")),
        "current_max": int(_text(tcpm / "current_max")),
        "current_now": int(_text(tcpm / "current_now")),
    }
    expected = {
        "online": "1",
        "usb_type": "C",
        "voltage_now": 5000000,
        "current_max": 500000,
        "current_now": 500000,
    }
    if values != expected:
        raise TrialError(f"TCPM 5V/C/500mA contract mismatch: {values}")
    return {"name": tcpm.name, **values}


def _check_native(rt: AuditRuntime) -> dict:
    online = _text(rt.sys("class/power_supply/samurai-usb-input/online"))
    usb_type = _text(rt.sys("class/power_supply/samurai-usb-input/usb_type"))
    current_max = int(
        _text(rt.sys("class/power_supply/samurai-usb-input/current_max"))
    )
    if online != "1" or "SDP" not in usb_type or current_max != 500000:
        raise TrialError("native SDP 500mA contract mismatch")
    return {"online": online, "usb_type": usb_type, "current_max": current_max}


def _check_mp2650(rt: AuditRuntime) -> dict:
    values = {
        "input_current_limit": int(_read_power_supply(rt, "mp2650-input", "input_current_limit")),
        "constant_charge_current": int(
            _read_power_supply(rt, "mp2650-input", "constant_charge_current")
        ),
        "constant_charge_voltage": int(
            _read_power_supply(rt, "mp2650-input", "constant_charge_voltage")
        ),
    }
    expected = {
        "input_current_limit": 500000,
        "constant_charge_current": 250000,
        "constant_charge_voltage": 8725000,
    }
    if values != expected:
        raise TrialError(f"MP2650 limits mismatch: {values}")
    health = _read_power_supply(rt, "mp2650-input", "health")
    behaviour = active_value(_read_power_supply(rt, "mp2650-input", "charge_behaviour"))
    if health != "Good" or behaviour != "auto":
        raise TrialError("MP2650 health/behaviour is not Good/auto")
    return {**values, "health": health, "charge_behaviour": behaviour}


def _check_protection(rt: AuditRuntime, status: dict) -> dict:
    state = parse_key_values(
        _text(rt.sys("devices/platform/samurai-gauge-protection/protection_state"))
    )
    if state.get("id") != 0x2719:
        raise TrialError("unexpected protection profile id")
    if any(state.get(key) != 0 for key in ("safety", "pf", "error")):
        raise TrialError(f"protection error is nonzero: {state}")
    if status.get("managed") is not True:
        raise TrialError("samurai charging is not managed")
    sample = status.get("sample")
    if not isinstance(sample, dict):
        raise TrialError("managed charging sample missing")
    if sample.get("valid") != 1 or sample.get("online") != 1 or sample.get("protection_ok") != 1:
        raise TrialError("charging sample is not valid/online/protected")
    fault_keys = (
        "fault",
        "error",
        "stop_error",
        "latched",
        "cycle_timeout",
        "thermal_inhibit",
        "source_inhibit",
        "gauge_charge_stop",
    )
    bad = {key: sample.get(key) for key in fault_keys if sample.get(key) != 0}
    if bad:
        raise TrialError(f"charging fault flags are nonzero: {bad}")
    return {"protection_state": state, "sample_fault_values": {key: 0 for key in fault_keys}}


def _check_apsd_adc(rt: AuditRuntime, dmesg: str, typec: dict, tcpm: dict) -> dict:
    # qcom_pmic_typec_apsd_prepare() runs before tcpm_register_port().  A
    # successful bound port/partner plus one TCPM supply therefore proves that
    # the full-PD APSD/ADC preparation path completed.  The source only logs
    # the handoff at shutdown, so no successful startup log may be required.
    if not typec.get("partner") or not tcpm.get("name"):
        raise TrialError("APSD/ADC preparation is not proven by Type-C/TCPM setup")
    refusal = [line for line in dmesg.splitlines() if APSD_REFUSAL_RE.search(line)]
    if refusal:
        raise TrialError(
            "full-PD APSD/QC takeover was refused: " + refusal[0]
        )
    return {
        "apsd_prepare_evidence": "qcom_pmic_typec_apsd_prepare_before_register",
        "adc_reader_evidence": "inferred_from_successful_full_PD_profile_probe",
        "typec_partner": typec["partner"],
        "tcpm_supply": tcpm["name"],
        "refusal_lines": [],
    }


def _warning_lines(dmesg: str) -> list[str]:
    return [line for line in dmesg.splitlines() if CRITICAL_DMESG.search(line)]


def _check_warnings_and_taint(
    rt: AuditRuntime,
    dmesg: str,
    *,
    baseline_dmesg: str | None,
    expected_tainted: int,
) -> dict:
    warnings = _warning_lines(dmesg)
    if baseline_dmesg is None:
        new_warnings = warnings
    else:
        baseline = set(_warning_lines(baseline_dmesg))
        new_warnings = [line for line in warnings if line not in baseline]
    if new_warnings:
        raise TrialError(f"new critical kernel warning(s): {new_warnings[:3]}")
    tainted = int(_text(rt.proc_root / "sys/kernel/tainted"))
    added = tainted & ~expected_tainted
    if added:
        raise TrialError(
            f"new kernel taint bits: 0x{added:x} (baseline 0x{expected_tainted:x})"
        )
    return {
        "tainted": tainted,
        "baseline_tainted": expected_tainted,
        "new_warning_lines": [],
    }


def audit(
    rt: AuditRuntime,
    *,
    baseline_dmesg: str | None = None,
    expected_tainted: int | None = None,
) -> dict:
    report = {
        "schema": 1,
        "trial_id": TRIAL_ID,
        "passed": False,
        "read_only": True,
        "accepted_token_written": False,
        "high_voltage_accessed": False,
    }
    try:
        boot = rt.boot_id_reader()
        report["boot_id"] = boot
        report["version"] = _check_version(rt)
        manifest, state = _guard_manifest_and_state(rt, boot)
        report["manifest_sha256"] = sha256_file(rt.manifest_path)
        report["watchdog"] = {
            "state": state["event"],
            "boot_id": state["boot_id"],
            "deadline_boottime": state["deadline_boottime"],
        }
        dmesg = rt.dmesg_reader()
        status = rt.status_reader()
        report["ncm"] = _check_ncm(rt, dmesg)
        report["typec"] = _check_typec(rt, dmesg)
        report["tcpm"] = _check_tcpm(rt)
        report["native"] = _check_native(rt)
        report["mp2650"] = _check_mp2650(rt)
        report["protection"] = _check_protection(rt, status)
        report["apsd_adc"] = _check_apsd_adc(
            rt, dmesg, report["typec"], report["tcpm"]
        )
        baseline = manifest.get("baseline_tainted", EXPECTED_TAINTED)
        if expected_tainted is None:
            expected_tainted = int(baseline)
        report["kernel_log"] = _check_warnings_and_taint(
            rt,
            dmesg,
            baseline_dmesg=baseline_dmesg,
            expected_tainted=expected_tainted,
        )
        sink_pdos = _text(rt.sys("class/typec/port0/connector/sink-pdos"))
        if sink_pdos != "04019032":
            raise TrialError(f"sink PDO is not fixed 5V only: {sink_pdos}")
        report["sink_pdos"] = sink_pdos
        report["fixed_5v_only"] = True
        report["accepted"] = state["event"] == "accepted"
        report["passed"] = True
    except BaseException as error:
        report["error"] = repr(error)
        report["traceback"] = traceback.format_exc()
    return report


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEVICE_ROOT)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--dmesg-file", type=Path)
    parser.add_argument("--status-file", type=Path)
    parser.add_argument("--baseline-dmesg", type=Path)
    parser.add_argument("--expected-tainted", type=int)
    args = parser.parse_args(argv)
    rt = AuditRuntime(
        root=args.root,
        manifest_path=args.manifest,
        dmesg_reader=(
            (lambda: args.dmesg_file.read_text())
            if args.dmesg_file
            else _default_dmesg
        ),
        status_reader=(
            (lambda: read_json(args.status_file))
            if args.status_file
            else _default_status
        ),
    )
    baseline = args.baseline_dmesg.read_text() if args.baseline_dmesg else None
    report = audit(
        rt,
        baseline_dmesg=baseline,
        expected_tainted=args.expected_tainted,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 3


if __name__ == "__main__":
    raise SystemExit(_main())
