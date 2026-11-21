"""Read-only postboot acceptance checks for the #528 trial.

This script only reads sysfs/procfs and runs read-only commands.  It does not
write an acceptance token, change charging parameters, or request a reboot.
"""
from __future__ import annotations

import argparse
import errno
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
    SERVICE_PATH,
    TRIAL_ID,
    VERSION,
    WATCH_SECONDS,
    TrialError,
    active_value,
    inspect_service_runlevel,
    parse_key_values,
    read_json,
    require_regular,
    runtime_kernel_version_matches,
    sha256_file,
    validate_service_runlevel,
)
from trial_guard import Runtime as GuardRuntime
from trial_guard import accepted_token, load_manifest, verify_installed


CRITICAL_DMESG = re.compile(
    r"(?i)(?:"
    r"\bWARNING:"
    r"|\bBUG:"
    r"|\bOops:"
    r"|\bCall Trace\b"
    r"|\bUnknown symbol\b"
    r"|\bdisagrees about version\b"
    r"|\bkernel panic\b"
    r")"
)
NCM_RE = re.compile(r"(?i)(cdc_ncm|CDC[ -]?NCM)")
TYPEC_BIND_RE = re.compile(r"(?i)(qcom,pmic-typec|qcom-pmic-typec)")
APSD_REFUSAL_RE = re.compile(r"(?i)full-PD APSD/QC takeover refused")
APSD_HANDOFF_PROPERTY = (
    "firmware/devicetree/base/soc@0/spmi@c440000/pmic@2/typec@1500/"
    "realme,apsd-handoff-trial"
)
TYPEC_SUPPLY_PROPERTY = (
    "firmware/devicetree/base/soc@0/geniqup@8c0000/i2c@884000/"
    "charger@5c/typec-supply"
)
USB_ADC_LABEL_PROPERTY = (
    "firmware/devicetree/base/soc@0/spmi@c440000/pmic@2/adc@3100/"
    "channel@8/label"
)
EUD_STATUS_PROPERTY = (
    "firmware/devicetree/base/soc@0/serial@88e0000/status"
)
EUD_OFF_ROUTE_STATUS_PROPERTY = (
    "firmware/devicetree/base/soc@0/eud-off-route/status"
)
TRANSIENT_READ_ERRNOS = {
    getattr(errno, name)
    for name in ("ENODATA", "EAGAIN", "ESTALE", "ENOLINK", "ETIMEDOUT")
    if hasattr(errno, name)
}
APSD_VBUS_MIN_UV = 4_400_000
APSD_VBUS_MAX_UV = 5_500_000
APSD_VBUS_SAMPLES = 3


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
        eud_route_binding_path: Path | None = None,
        runlevel_reader=None,
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
        self.eud_route_binding_path = (
            Path(eud_route_binding_path)
            if eud_route_binding_path is not None
            else None
        )
        self.runlevel_reader = runlevel_reader
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
    # A single PMIC/regmap read can return ENODATA while a poll is in flight.
    # Retry only known transient errors; real missing files or persistent
    # failures still fail closed.
    for attempt in range(5):
        try:
            return path.read_text().strip()
        except OSError as error:
            if error.errno not in TRANSIENT_READ_ERRNOS or attempt == 4:
                raise
            time.sleep(0.02)
    raise AssertionError("unreachable")


def _read_power_supply(rt: AuditRuntime, name: str, field: str) -> str:
    return _text(rt.sys(f"class/power_supply/{name}/{field}"))


def _battery_power_supply(rt: AuditRuntime) -> Path:
    power = rt.sys("class/power_supply")
    candidates = (
        [
            entry
            for entry in power.iterdir()
            if entry.is_dir()
            and (entry / "type").is_file()
            and _text(entry / "type") == "Battery"
        ]
        if power.is_dir()
        else []
    )
    if len(candidates) != 1:
        raise TrialError(
            f"expected exactly one Battery power supply, found {[p.name for p in candidates]}"
        )
    return candidates[0]


def _check_version(rt: AuditRuntime) -> str:
    version = rt.version_reader()
    if not runtime_kernel_version_matches(version, VERSION):
        raise TrialError(f"kernel version is not {VERSION!r}: {version!r}")
    return version


def _guard_manifest_and_state(
    rt: AuditRuntime, boot: str
) -> tuple[dict, dict, dict]:
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
    stage = read_json(rt.root / "stage.json")
    stage_runlevel = validate_service_runlevel(stage.get("service_runlevel"))
    current_runlevel = (
        rt.runlevel_reader()
        if rt.runlevel_reader is not None
        else inspect_service_runlevel(rt.target_root)
    )
    current_runlevel = validate_service_runlevel(current_runlevel)
    if current_runlevel["before"] != "enabled":
        raise TrialError("samurai-charging is not enabled in the default runlevel")
    if current_runlevel["link_target"] != SERVICE_PATH.as_posix():
        raise TrialError("default runlevel link target is not the trial service")
    if stage_runlevel["before"] == "missing" and stage_runlevel["added"] is not True:
        raise TrialError("stage receipt does not prove it added the runlevel link")
    state = read_json(rt.root / "state.json")
    if state.get("boot_id") != boot:
        raise TrialError("guard state belongs to a different boot")
    event = state.get("event")
    if event not in {"watchdog-running", "accepted"}:
        raise TrialError("guard watchdog is not armed on this boot")
    deadline = state.get("deadline_boottime")
    token_ok = accepted_token(guard_rt, manifest)
    if event == "watchdog-running":
        if type(deadline) not in {int, float}:
            raise TrialError("watchdog deadline missing")
        pid = state.get("pid")
        process = rt.proc_root / str(pid)
        if type(pid) is not int or pid <= 1 or not process.is_dir():
            raise TrialError("watchdog process is not alive")
        try:
            argv = (process / "cmdline").read_bytes().split(b"\0")
            proc_state = (process / "stat").read_text().rsplit(")", 1)[1].split()[0]
        except (OSError, IndexError) as error:
            raise TrialError("watchdog process evidence is unreadable") from error
        if not any(arg.endswith(b"trial_guard.py") for arg in argv) or b"watch" not in argv:
            raise TrialError("watchdog pid does not identify the guard watch process")
        if proc_state in {"Z", "X"}:
            raise TrialError("watchdog process has exited")
    elif not token_ok:
        raise TrialError("accepted guard state has no valid acceptance token")
    if not token_ok:
        elapsed = rt.boottime() - float(deadline) + WATCH_SECONDS
        if elapsed >= WATCH_SECONDS:
            raise TrialError("read-only audit started after the unaccepted deadline")
    readback = read_json(rt.root / "carrier-readback.json")
    if (
        readback.get("schema") != 1
        or readback.get("source") != "guard"
        or readback.get("boot_id") != boot
    ):
        raise TrialError("guard carrier readback evidence is not for this boot")
    for name in ("boot", "logdump"):
        row = readback.get("carriers", {}).get(name)
        expected = manifest["carriers"][name]["new"]
        if (
            not isinstance(row, dict)
            or row.get("sha256") != expected
            or row.get("expected") != expected
            or row.get("bytes") != manifest["carriers"][name]["bytes"]
        ):
            raise TrialError(f"guard carrier readback mismatch: {name}")
        if readback["partition_identity"].get(name) != stage["partition_identity"].get(name):
            raise TrialError(f"guard carrier identity mismatch: {name}")
    return manifest, state, readback, current_runlevel


def _check_ncm(rt: AuditRuntime, dmesg: str) -> dict:
    lines = [line for line in dmesg.splitlines() if NCM_RE.search(line)]
    driver_found = []
    reachable = False
    net = rt.sys("class/net")
    if net.is_dir():
        for entry in net.iterdir():
            driver = _driver_name(entry / "device/driver")
            if driver and (
                driver == "cdc_ncm"
                or driver.startswith("configfs-gadget")
                or driver == "u_ether"
            ):
                driver_found.append(entry.name)
                if entry.name == "usb0":
                    reachable = True
    if not driver_found:
        raise TrialError("no USB gadget NCM interface is bound")
    if not reachable:
        raise TrialError("usb0 NCM interface is missing")
    return {
        "dmesg": lines,
        "interfaces": sorted(driver_found),
        "reachable_interface": "usb0",
    }


def _check_eud_route(rt: AuditRuntime) -> dict:
    eud_status = _text(rt.sys(EUD_STATUS_PROPERTY)).rstrip("\x00")
    route_status = _text(rt.sys(EUD_OFF_ROUTE_STATUS_PROPERTY)).rstrip("\x00")
    if eud_status != "disabled":
        raise TrialError(f"EUD COM must stay disabled, got {eud_status!r}")
    if route_status != "okay":
        raise TrialError(f"EUD-off route must stay enabled, got {route_status!r}")
    binding = rt.eud_route_binding_path or rt.sys(
        "bus/platform/drivers/samurai-eud-off-route/soc@0:eud-off-route"
    )
    if not binding.exists():
        raise TrialError("samurai-eud-off-route binding is missing")
    if rt.require_symlinks and not binding.is_symlink():
        raise TrialError("samurai-eud-off-route binding is not a sysfs symlink")
    return {
        "eud_com_status": eud_status,
        "route_status": route_status,
        "route_binding": "soc@0:eud-off-route",
    }


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
    # The legacy BC1.2 observer is informational after TCPM takes ownership.
    # Its classification/budget can retain stale CDP values even while the live
    # Type-C source, TCPM contract, and MP2650 input limit are the active path.
    return {
        "online": online,
        "usb_type": usb_type,
        "current_max": current_max,
        "authoritative": False,
    }


def _check_mp2650(rt: AuditRuntime, status: dict) -> dict:
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
        "constant_charge_current": 250000,
        "constant_charge_voltage": 8725000,
    }
    if any(values[key] != value for key, value in expected.items()):
        raise TrialError(f"MP2650 limits mismatch: {values}")
    if not 500000 <= values["input_current_limit"] <= 900000:
        raise TrialError(f"MP2650 hardware input limit is unsafe: {values}")
    sample = status.get("sample")
    if not isinstance(sample, dict) or sample.get("budget_ua") != 500000:
        raise TrialError(
            f"managed TCPM input budget is not 500000 uA: {sample!r}"
        )
    health = _read_power_supply(rt, "mp2650-input", "health")
    behaviour = active_value(_read_power_supply(rt, "mp2650-input", "charge_behaviour"))
    if health != "Good" or behaviour != "auto":
        raise TrialError("MP2650 health/behaviour is not Good/auto")
    return {
        **values,
        "health": health,
        "charge_behaviour": behaviour,
        "managed_budget_ua": sample["budget_ua"],
    }


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
    for key in ("valid", "online", "protection_ok"):
        if type(sample.get(key)) is not int or sample.get(key) != 1:
            raise TrialError("charging sample is not valid/online/protected")
    if type(sample.get("shadow")) is not int or sample.get("shadow") != 0:
        raise TrialError("charging sample is from shadow mode")
    age_ms = sample.get("age_ms")
    if type(age_ms) is not int or age_ms < 0 or age_ms > 3000:
        raise TrialError(f"charging sample is stale: age_ms={age_ms!r}")
    desired_enable = sample.get("desired_enable")
    if type(desired_enable) is not int:
        raise TrialError("charging sample lacks desired_enable")
    normal = (
        desired_enable == 1
        and sample.get("hold_requested") == 0
        and sample.get("full_holding") == 0
    )
    full_hold = (
        desired_enable == 0
        and sample.get("logical_full") == 1
        and sample.get("hold_requested") == 1
        and sample.get("full_holding") == 1
        and sample.get("full_cause") in (1, 2, 3)
    )
    if not (normal or full_hold):
        raise TrialError(
            "charging sample is neither actively enabled nor an explicit full hold"
        )
    battery = _battery_power_supply(rt)
    battery_status = _text(battery / "status")
    mp2650_status = _read_power_supply(rt, "mp2650-input", "status")
    if full_hold:
        if battery_status != "Full":
            raise TrialError(
                f"Full hold is not exposed by {battery.name}/status: {battery_status!r}"
            )
        # CHG is intentionally disabled during full hold. The MP2650 may expose
        # that as either Full (before the stop settles) or Not charging.
        if mp2650_status not in ("Full", "Not charging"):
            raise TrialError(
                f"Full hold has unexpected mp2650-input/status: {mp2650_status!r}"
            )
    else:
        if battery_status not in ("Charging", "Not charging"):
            raise TrialError(
                f"active charging has inconsistent {battery.name}/status: {battery_status!r}"
            )
        if mp2650_status not in ("Charging", "Not charging"):
            raise TrialError(
                f"active charging has inconsistent mp2650-input/status: {mp2650_status!r}"
            )
        if battery_status != "Charging" and mp2650_status != "Charging":
            raise TrialError(
                "active charging state has no Charging indicator from battery or MP2650"
            )
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
    return {
        "protection_state": state,
        "sample_mode": "active" if normal else "full-hold",
        "battery_status": battery_status,
        "battery_name": battery.name,
        "mp2650_status": mp2650_status,
        "sample_age_ms": age_ms,
        "sample_fault_values": {key: 0 for key in fault_keys},
    }


def _check_apsd_adc(rt: AuditRuntime, dmesg: str, typec: dict, tcpm: dict) -> dict:
    # qcom_pmic_typec_apsd_prepare() runs before tcpm_register_port(). Read the
    # same processed ADC5 channel directly instead of inferring success from
    # Type-C setup alone. The source only logs the handoff at shutdown.
    if not typec.get("partner") or not tcpm.get("name"):
        raise TrialError("APSD/ADC preparation is not proven by Type-C/TCPM setup")
    typec_supply = rt.sys(TYPEC_SUPPLY_PROPERTY)
    if not typec_supply.is_file():
        raise TrialError("typec-supply DT property is missing")
    adc_label = rt.sys(USB_ADC_LABEL_PROPERTY)
    if not adc_label.is_file():
        raise TrialError("usb_in_v_div_16 DT property is missing")
    try:
        label = adc_label.read_bytes().rstrip(b"\0").decode("ascii")
    except (OSError, UnicodeDecodeError) as error:
        raise TrialError("usb_in_v_div_16 DT property is unreadable") from error
    if label != "usb_in_v_div_16":
        raise TrialError(f"unexpected usb_in_v_div_16 DT label: {label!r}")
    property_path = rt.sys(APSD_HANDOFF_PROPERTY)
    if not property_path.is_file():
        raise TrialError("realme,apsd-handoff-trial DT property is missing")
    refusal = [line for line in dmesg.splitlines() if APSD_REFUSAL_RE.search(line)]
    if refusal:
        raise TrialError(
            "full-PD APSD/QC takeover was refused: " + refusal[0]
        )
    iio_devices = rt.sys("bus/iio/devices")
    candidates = []
    if iio_devices.is_dir():
        for device in sorted(iio_devices.iterdir()):
            name_path = device / "name"
            label_path = device / "in_voltage_usb_in_v_div_16_label"
            input_path = device / "in_voltage_usb_in_v_div_16_input"
            if not (name_path.is_file() and label_path.is_file() and input_path.is_file()):
                continue
            device_name = _text(name_path)
            if "adc@3100" not in device_name and "qcom-spmi-adc5" not in device_name:
                continue
            if _text(label_path) != "usb_in_v_div_16":
                continue
            candidates.append((device, device_name, input_path))
    if len(candidates) != 1:
        raise TrialError("expected exactly one PM8150B ADC5 usb_in_v_div_16 channel")
    device, device_name, input_path = candidates[0]
    samples = [int(_text(input_path)) for _ in range(APSD_VBUS_SAMPLES)]
    if any(
        sample < APSD_VBUS_MIN_UV or sample > APSD_VBUS_MAX_UV
        for sample in samples
    ):
        raise TrialError(
            f"APSD ADC/VBUS samples outside {APSD_VBUS_MIN_UV}.."
            f"{APSD_VBUS_MAX_UV} uV: {samples}"
        )
    return {
        "apsd_prepare_evidence": "qcom_pmic_typec_apsd_prepare_before_register",
        "adc_reader_evidence": "direct_processed_PM8150B_ADC5_usb_in_v_div_16",
        "adc_device": device.name,
        "adc_device_name": device_name,
        "adc_channel": "usb_in_v_div_16",
        "adc_samples_uv": samples,
        "adc_window_uv": [APSD_VBUS_MIN_UV, APSD_VBUS_MAX_UV],
        "dt_typec_supply": "charger@5c/typec-supply (present)",
        "dt_adc_label": "adc@3100/channel@8/label=usb_in_v_div_16",
        "explicit_handoff_property": "realme,apsd-handoff-trial (present)",
        "bounded_retry": "2s total / 20ms interval for transient startup state",
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
        manifest, state, readback, runlevel = _guard_manifest_and_state(rt, boot)
        report["manifest_sha256"] = sha256_file(rt.manifest_path)
        report["service_runlevel"] = runlevel
        report["watchdog"] = {
            "state": state["event"],
            "boot_id": state["boot_id"],
        }
        if type(state.get("deadline_boottime")) in {int, float}:
            report["watchdog"]["deadline_boottime"] = state["deadline_boottime"]
        report["carrier_readback"] = readback
        dmesg = rt.dmesg_reader()
        status = rt.status_reader()
        report["eud_route"] = _check_eud_route(rt)
        report["ncm"] = _check_ncm(rt, dmesg)
        report["typec"] = _check_typec(rt, dmesg)
        report["tcpm"] = _check_tcpm(rt)
        report["native"] = _check_native(rt)
        report["mp2650"] = _check_mp2650(rt, status)
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
        # This kernel does not expose sink-pdos through the Type-C class. The
        # fixed 5 V-only contract is enforced in the Image and verified through
        # the live TCPM voltage/current values above.
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
