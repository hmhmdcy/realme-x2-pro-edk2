from __future__ import annotations

import copy
import unittest

import audit_soak


def sample(seconds: int, *, ip: str = "169.254.42.1") -> dict:
    return {
        "schema": 1,
        "timestamp": f"2026-10-27T01:{seconds // 60:02d}:{seconds % 60:02d}+08:00",
        "reachable": True,
        "ssh_ip": ip,
        "sample_seconds": 0.5,
        "device": {
            "boot_id": audit_soak.EXPECTED_BOOT,
            "audit_boot": audit_soak.EXPECTED_BOOT,
            "accepted_boot": audit_soak.EXPECTED_BOOT,
            "audit_passed": True,
            "audit_manifest_sha256": audit_soak.EXPECTED_MANIFEST,
            "state_event": "accepted",
            "version": audit_soak.EXPECTED_VERSION,
            "protection_health": "Good",
            "battery_health": "Good",
            "mp_health": "Good",
            "mp_online": 1,
            "tcpm_voltage_uv": 5_000_000,
            "tcpm_current_ua": 500_000,
            "battery_voltage_uv": 8_650_000,
            "battery_temp_decic": 280,
            "tainted": "4096",
            "telemetry": {
                "valid": 1,
                "online": 1,
                "protection_ok": 1,
                "shadow": 0,
                "age_ms": 100,
                "desired_enable": 1,
                "logical_full": 0,
                "full_holding": 0,
                "hold_requested": 0,
                "full_cause": 0,
                "cycle_timeout": 0,
                "error": 0,
                "fault": 0,
                "gauge_charge_stop": 0,
                "latched": 0,
                "source_inhibit": 0,
                "stop_error": 0,
                "thermal_inhibit": 0,
            },
            "thermal_zones": {
                "thermal_zone0": {"temp_millideg": 36_000},
            },
        },
    }


def rows() -> list[dict]:
    return [sample(0), sample(60), sample(120)]


class SoakAuditTests(unittest.TestCase):
    def test_complete_healthy_window_passes(self) -> None:
        report = audit_soak.audit(rows(), minimum_samples=3, minimum_span_seconds=120)
        self.assertTrue(report["passed"], report)
        self.assertEqual(report["transport_counts"], {"169.254.42.1": 3})

    def test_wifi_transport_does_not_prove_physical_usb(self) -> None:
        value = rows()
        for row in value:
            row["ssh_ip"] = "192.168.0.114"
        report = audit_soak.audit(value, minimum_samples=3, minimum_span_seconds=120)
        self.assertTrue(report["passed"], report)
        self.assertEqual(report["usb_transport_samples"], 0)
        self.assertFalse(report["physical_usb_cycle_proven"])

    def test_single_unreachable_sample_fails(self) -> None:
        value = rows()
        value[1] = {
            "schema": 1,
            "timestamp": value[1]["timestamp"],
            "reachable": False,
            "ssh_ip": None,
        }
        report = audit_soak.audit(value, minimum_samples=3)
        self.assertFalse(report["passed"])
        self.assertIn("unreachable", " ".join(report["errors"]))

    def test_boot_change_fails(self) -> None:
        value = rows()
        value[2]["device"]["boot_id"] = "33333333-3333-3333-3333-333333333333"
        report = audit_soak.audit(value, minimum_samples=3)
        self.assertFalse(report["passed"])
        self.assertIn("unexpected boot", " ".join(report["errors"]))

    def test_fault_and_stale_sample_fail(self) -> None:
        value = rows()
        value[1]["device"]["telemetry"]["fault"] = 1
        value[2]["device"]["telemetry"]["age_ms"] = 5000
        report = audit_soak.audit(value, minimum_samples=3)
        self.assertFalse(report["passed"])
        errors = " ".join(report["errors"])
        self.assertIn("fault is nonzero", errors)
        self.assertIn("stale", errors)

    def test_full_hold_and_large_gap(self) -> None:
        value = rows()
        telemetry = value[1]["device"]["telemetry"]
        telemetry.update(
            desired_enable=0,
            logical_full=1,
            full_holding=1,
            hold_requested=1,
            full_cause=3,
        )
        report = audit_soak.audit(value, minimum_samples=3, maximum_gap_seconds=30)
        self.assertFalse(report["passed"])
        self.assertIn("maximum sample gap", " ".join(report["errors"]))
        report = audit_soak.audit(value, minimum_samples=3, maximum_gap_seconds=60)
        self.assertTrue(report["passed"], report)

    def test_manifest_mismatch_fails(self) -> None:
        value = copy.deepcopy(rows())
        value[0]["device"]["audit_manifest_sha256"] = "0" * 64
        report = audit_soak.audit(value, minimum_samples=3)
        self.assertFalse(report["passed"])
        self.assertIn("manifest hash mismatch", " ".join(report["errors"]))


if __name__ == "__main__":
    unittest.main()
