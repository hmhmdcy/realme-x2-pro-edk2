from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


TRIAL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TRIAL_DIR))

import physical_cycle_worker as cycle  # noqa: E402


def telemetry(
    *,
    online: bool,
    session_seconds: int,
    full_hold: bool = False,
    protection_ok: bool = True,
    fault: bool = False,
) -> dict:
    active = online and not full_hold
    return {
        "valid": 1,
        "online": int(online),
        "desired_enable": int(active),
        "logical_full": int(full_hold),
        "full_holding": int(full_hold),
        "hold_requested": int(full_hold),
        "full_cause": 2 if full_hold else 0,
        "protection_ok": int(protection_ok),
        "shadow": 0,
        "age_ms": 100,
        "session_seconds": session_seconds,
        "error": 0,
        "stop_error": 0,
        "latched": 0,
        "source_inhibit": 0,
        "fault": int(fault),
        "cycle_timeout": 0,
        "thermal_inhibit": 0,
        "gauge_charge_stop": 0,
    }


def sample(
    boottime: float,
    *,
    online: bool,
    session_seconds: int,
    full_hold: bool = False,
    protection_ok: bool = True,
    fault: bool = False,
) -> dict:
    return {
        "epoch": 1000.0 + boottime,
        "boottime": boottime,
        "telemetry": telemetry(
            online=online,
            session_seconds=session_seconds,
            full_hold=full_hold,
            protection_ok=protection_ok,
            fault=fault,
        ),
        "source_online": "1" if online else "0",
        "source_current_max": "500000",
        "source_input_current_limit": "500000" if online else "0",
        "source_usb_type": "SDP",
        "mp_input_current_limit": "500000" if online else "0",
        "battery_name": "bq28z610-0",
        "mp_status": (
            "Full" if full_hold else ("Charging" if online else "Not charging")
        ),
        "battery_status": (
            "Full" if full_hold else ("Charging" if online else "Not charging")
        ),
        "mp_health": "Good",
        "protection_health": "Good" if protection_ok else "Bad",
        "udc_state": "configured" if online else "",
    }


def healthy(
    boottime: float,
    *,
    session_seconds: int,
    full_hold: bool = False,
) -> dict:
    return sample(
        boottime,
        online=True,
        session_seconds=session_seconds,
        full_hold=full_hold,
    )


def detached(boottime: float) -> dict:
    return sample(boottime, online=False, session_seconds=0)


def protection_fault(boottime: float) -> dict:
    row = sample(
        boottime,
        online=True,
        session_seconds=0,
        protection_ok=False,
        fault=True,
    )
    row["protection_health"] = "Bad"
    return row


def cycle_samples(
    *,
    detach_times: tuple[float, ...] = (3.0, 4.0, 5.0),
    recovery_start: float = 6.0,
    recovery_count: int = 15,
    recovery_step: float = 1.0,
    recovery_full_hold: bool = False,
) -> list[dict]:
    rows = [
        healthy(0.0, session_seconds=98),
        healthy(1.0, session_seconds=99),
        healthy(2.0, session_seconds=100),
    ]
    rows.extend(detached(value) for value in detach_times)
    for index in range(recovery_count):
        rows.append(
            healthy(
                recovery_start + index * recovery_step,
                session_seconds=(
                    101 + index if recovery_full_hold else index
                ),
                full_hold=recovery_full_hold,
            )
        )
    return rows


def classify(
    samples: list[dict],
    *,
    same_boot: bool = True,
    manifest_unchanged: bool = True,
    taint_before: int = 0,
    taint_after: int = 0,
    critical_delta: list[str] | None = None,
) -> dict:
    return cycle.classify_cycle(
        samples,
        same_boot=same_boot,
        manifest_unchanged=manifest_unchanged,
        taint_before=taint_before,
        taint_after=taint_after,
        critical_delta=[] if critical_delta is None else critical_delta,
    )


class PhysicalCycleTests(unittest.TestCase):
    def test_worker_accepts_only_absent_or_empty_evidence_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            absent = base / "absent"
            cycle._prepare_root(absent)
            self.assertTrue(absent.is_dir())

            empty = base / "empty"
            empty.mkdir()
            cycle._prepare_root(empty)

            nonempty = base / "nonempty"
            nonempty.mkdir()
            (nonempty / "sentinel").write_text("x")
            with self.assertRaisesRegex(RuntimeError, "absent or empty"):
                cycle._prepare_root(nonempty)

    def test_launcher_leaves_evidence_creation_to_worker(self) -> None:
        launcher = (TRIAL_DIR / "Invoke-PhysicalUsbCycle.ps1").read_text()
        self.assertTrue(launcher.startswith("#requires -Version 7.0\n"))
        self.assertIn("mkdir -p '$remote'", launcher)
        self.assertNotIn("mkdir -p '$evidence'", launcher)
        self.assertIn("[string]$WorkerPath,", launcher)
        self.assertIn(
            'if (-not $WorkerPath) {\n'
            '    $WorkerPath = Join-Path $PSScriptRoot "physical_cycle_worker.py"\n'
            '}',
            launcher,
        )
        self.assertNotIn('[string]$WorkerPath = (Join-Path $PSScriptRoot', launcher)

    def test_accepted_healthy_cycle_starts_a_fresh_session(self) -> None:
        result = classify(cycle_samples())
        self.assertTrue(result["accepted"], result["checks"])
        self.assertTrue(result["new_session"])
        self.assertFalse(result["after_full_hold"])
        self.assertTrue(result["physical_usb_cycle_proven"])
        self.assertEqual(result["baseline_samples"], 3)
        self.assertEqual(result["detached_samples"], 3)
        self.assertEqual(result["detached_span_seconds"], 2.0)
        self.assertEqual(result["recovered_samples"], 15)
        self.assertEqual(result["recovered_span_seconds"], 14.0)
        self.assertTrue(result["checks"]["recovered_sdp_500ma"])
        self.assertTrue(result["checks"]["recovered_protection"])

    def test_full_hold_recovery_does_not_require_a_new_session(self) -> None:
        result = classify(cycle_samples(recovery_full_hold=True))
        self.assertTrue(result["accepted"], result["checks"])
        self.assertFalse(result["new_session"])
        self.assertTrue(result["after_full_hold"])
        self.assertTrue(result["checks"]["fresh_session_or_full_hold"])

    def test_full_hold_accepts_charger_disabled_status(self) -> None:
        rows = cycle_samples(recovery_full_hold=True)
        for row in rows[6:]:
            row["mp_status"] = "Not charging"
        result = classify(rows)
        self.assertTrue(result["accepted"], result["checks"])
        self.assertTrue(result["after_full_hold"])

    def test_active_recovery_without_a_new_session_is_rejected(self) -> None:
        rows = cycle_samples()
        for index, row in enumerate(rows[6:]):
            row["telemetry"]["session_seconds"] = 101 + index
        result = classify(rows)
        self.assertFalse(result["accepted"])
        self.assertFalse(result["new_session"])
        self.assertFalse(result["after_full_hold"])
        self.assertFalse(result["checks"]["fresh_session_or_full_hold"])

    def test_no_detach_is_rejected(self) -> None:
        rows = [healthy(float(index), session_seconds=100 + index) for index in range(20)]
        result = classify(rows)
        self.assertFalse(result["accepted"])
        self.assertFalse(result["checks"]["physical_detach_confirmed"])
        self.assertEqual(result["detached_samples"], 0)

    def test_detach_shorter_than_two_seconds_is_rejected(self) -> None:
        rows = cycle_samples(
            detach_times=(3.0, 4.0, 4.9),
            recovery_start=5.9,
        )
        result = classify(rows)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["detached_samples"], 3)
        self.assertLess(result["detached_span_seconds"], 2.0)
        self.assertFalse(result["checks"]["physical_detach_confirmed"])

    def test_detach_segment_must_be_contiguous(self) -> None:
        rows = cycle_samples()
        rows.insert(4, healthy(3.5, session_seconds=100))
        result = classify(rows)
        self.assertFalse(result["accepted"])
        self.assertFalse(result["checks"]["physical_detach_confirmed"])
        self.assertLess(result["detached_samples"], 3)

    def test_recovery_shorter_than_fifteen_samples_is_rejected(self) -> None:
        result = classify(cycle_samples(recovery_count=14))
        self.assertFalse(result["accepted"])
        self.assertEqual(result["recovered_samples"], 14)
        self.assertFalse(result["checks"]["automatic_recovery"])

    def test_recovery_shorter_than_fourteen_seconds_is_rejected(self) -> None:
        result = classify(
            cycle_samples(
                recovery_count=15,
                recovery_step=13.9 / 14,
            )
        )
        self.assertFalse(result["accepted"])
        self.assertEqual(result["recovered_samples"], 15)
        self.assertLess(result["recovered_span_seconds"], 14.0)
        self.assertFalse(result["checks"]["automatic_recovery"])

    def test_persistent_protection_fault_is_rejected(self) -> None:
        rows = [
            healthy(0.0, session_seconds=98),
            healthy(1.0, session_seconds=99),
            healthy(2.0, session_seconds=100),
            detached(3.0),
            detached(4.0),
            detached(5.0),
        ]
        rows.extend(protection_fault(6.0 + index) for index in range(15))
        result = classify(rows)
        self.assertFalse(result["accepted"])
        self.assertFalse(result["checks"]["automatic_recovery"])
        self.assertFalse(result["checks"]["recovered_protection"])

    def test_active_recovery_with_stale_full_status_is_rejected(self) -> None:
        rows = cycle_samples()
        rows[-1]["battery_status"] = "Full"
        result = classify(rows)
        self.assertFalse(result["accepted"])
        self.assertFalse(result["checks"]["automatic_recovery"])

    def test_active_recovery_with_stale_mp_full_status_is_rejected(self) -> None:
        rows = cycle_samples()
        rows[-1]["mp_status"] = "Full"
        result = classify(rows)
        self.assertFalse(result["accepted"])
        self.assertFalse(result["checks"]["automatic_recovery"])

    def test_active_recovery_without_charging_indicator_is_rejected(self) -> None:
        rows = cycle_samples()
        rows[-1]["battery_status"] = "Not charging"
        rows[-1]["mp_status"] = "Not charging"
        result = classify(rows)
        self.assertFalse(result["accepted"])
        self.assertFalse(result["checks"]["automatic_recovery"])

    def test_gauge_charge_stop_prevents_healthy_recovery(self) -> None:
        rows = cycle_samples()
        rows[-1]["telemetry"]["gauge_charge_stop"] = 1
        result = classify(rows)
        self.assertFalse(result["accepted"])
        self.assertFalse(result["checks"]["automatic_recovery"])

    def test_full_hold_recovery_rejects_active_charger_status(self) -> None:
        rows = cycle_samples(recovery_full_hold=True)
        rows[-1]["mp_status"] = "Charging"
        result = classify(rows)
        self.assertFalse(result["accepted"])
        self.assertFalse(result["checks"]["automatic_recovery"])

    def test_full_hold_recovery_rejects_non_full_battery_status(self) -> None:
        rows = cycle_samples(recovery_full_hold=True)
        rows[-1]["battery_status"] = "Not charging"
        result = classify(rows)
        self.assertFalse(result["accepted"])
        self.assertFalse(result["checks"]["automatic_recovery"])

    def test_full_hold_cause_range_is_exact(self) -> None:
        row = cycle_samples(recovery_full_hold=True)[-1]
        for cause in (1, 2, 3):
            with self.subTest(cause=cause):
                row["telemetry"]["full_cause"] = cause
                self.assertTrue(cycle.full_hold_telemetry(row["telemetry"]))
        for cause in (0, 4):
            with self.subTest(cause=cause):
                row["telemetry"]["full_cause"] = cause
                self.assertFalse(cycle.full_hold_telemetry(row["telemetry"]))

    def test_full_hold_diagnostic_requires_complete_telemetry(self) -> None:
        for field in ("logical_full", "hold_requested"):
            with self.subTest(field=field):
                rows = cycle_samples(recovery_full_hold=True)
                rows[-1]["telemetry"][field] = 0
                result = classify(rows)
                self.assertFalse(result["accepted"])
                self.assertFalse(result["after_full_hold"])
                self.assertFalse(result["checks"]["fresh_session_or_full_hold"])

    def test_transient_protection_fault_during_recovery_is_rejected(self) -> None:
        rows = cycle_samples()
        rows.insert(9, protection_fault(9.0))
        result = classify(rows)
        self.assertFalse(result["accepted"])
        self.assertFalse(result["checks"]["no_safety_fault_during_cycle"])
        self.assertFalse(result["checks"]["automatic_recovery"])
        self.assertFalse(result["no_safety_fault_during_cycle"])

    def test_boot_change_is_rejected(self) -> None:
        result = classify(cycle_samples(), same_boot=False)
        self.assertFalse(result["accepted"])
        self.assertFalse(result["checks"]["same_boot"])
        self.assertFalse(result["same_boot"])

    def test_manifest_change_is_rejected(self) -> None:
        result = classify(cycle_samples(), manifest_unchanged=False)
        self.assertFalse(result["accepted"])
        self.assertFalse(result["checks"]["manifest_unchanged"])
        self.assertFalse(result["manifest_unchanged"])

    def test_taint_change_is_rejected(self) -> None:
        result = classify(cycle_samples(), taint_before=0, taint_after=1)
        self.assertFalse(result["accepted"])
        self.assertFalse(result["checks"]["taint_unchanged"])
        self.assertEqual(result["taint_after"], 1)

    def test_new_critical_dmesg_is_rejected(self) -> None:
        result = classify(
            cycle_samples(),
            critical_delta=["Oops: 0000 [#1] SMP"],
        )
        self.assertFalse(result["accepted"])
        self.assertFalse(result["checks"]["no_new_critical_log"])
        self.assertEqual(result["critical_log_delta"], ["Oops: 0000 [#1] SMP"])


if __name__ == "__main__":
    unittest.main()
