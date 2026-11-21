from __future__ import annotations

import sys
import unittest
from pathlib import Path


TRIAL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TRIAL_DIR))

import physical_wake_worker as wake  # noqa: E402


def snapshot(
    online: str,
    *,
    success: int,
    event_counts: tuple[int, int],
    rtc_count: int,
    epoch: float,
    tail: str,
    pm_wakeup_irq: str = "0",
) -> dict:
    return {
        "boot_id": "boot-1",
        "version": "Linux #517 SMP PREEMPT test",
        "boottime_ns": 1,
        "epoch": epoch,
        "mem_sleep": "[s2idle]",
        "rtc_alarm": "",
        "rtc_wakeup": "enabled",
        "pm_wakeup_irq": pm_wakeup_irq,
        "psy": {
            "online": online,
            "current_max": "500000",
            "input_current_limit": "500000" if online == "1" else "0",
            "status": "Charging" if online == "1" else "Discharging",
            "usb_type": "SDP",
            "power/wakeup": "enabled",
        },
        "stats": {"success": success, "fail": 0},
        "interrupts": {
            "rows": {
                40: {"count": event_counts[0], "line": "40: 1 usbin-plugin"},
                41: {"count": event_counts[1], "line": "41: 1 usbin-src-change"},
                42: {"count": rtc_count, "line": "42: 1 rtc0"},
            }
        },
        "wakeup_sources": {},
        "dmesg": {"bytes": len(tail), "sha256": "x", "tail": tail},
    }


class PhysicalWakeTests(unittest.TestCase):
    def test_insert_wake_with_owned_irq_and_no_rtc_is_accepted(self) -> None:
        before = snapshot(
            "0",
            success=1,
            event_counts=(10, 10),
            rtc_count=5,
            epoch=100.0,
            tail="baseline\n",
        )
        after_tail = (
            "baseline\n"
            "[ 10] PM: suspend entry (s2idle)\n"
            "[ 20] usb usb0: reset\n"
            "[ 21] PM: suspend exit\n"
        )
        after = snapshot(
            "1",
            success=2,
            event_counts=(11, 10),
            rtc_count=5,
            epoch=125.0,
            tail=after_tail,
            pm_wakeup_irq="40",
        )
        result = wake.classify(
            "insert",
            before,
            after,
            event_irqs={"usbin-plugin": 40, "usbin-src-change": 41},
            rtc_irq=42,
            request_epoch=100.0,
            alarm_seconds=180,
        )
        self.assertTrue(result["accepted"], result["errors"])
        self.assertTrue(result["pm_wakeup_irq_is_owned_event"])
        self.assertEqual(result["event_irq_deltas"]["usbin-plugin"], 1)

    def test_remove_wake_without_event_irq_fails(self) -> None:
        before = snapshot(
            "1",
            success=1,
            event_counts=(10, 10),
            rtc_count=5,
            epoch=100.0,
            tail="baseline\n",
        )
        after = snapshot(
            "0",
            success=2,
            event_counts=(10, 10),
            rtc_count=5,
            epoch=125.0,
            tail="baseline\nPM: suspend entry (s2idle)\nPM: suspend exit\n",
        )
        result = wake.classify(
            "remove",
            before,
            after,
            event_irqs={"usbin-plugin": 40, "usbin-src-change": 41},
            rtc_irq=42,
            request_epoch=100.0,
            alarm_seconds=180,
        )
        self.assertFalse(result["accepted"])
        self.assertIn("neither owned USB event IRQ advanced", result["errors"])

    def test_rtc_fallback_is_never_accepted(self) -> None:
        before = snapshot(
            "1",
            success=1,
            event_counts=(10, 10),
            rtc_count=5,
            epoch=100.0,
            tail="baseline\n",
        )
        after = snapshot(
            "0",
            success=2,
            event_counts=(11, 10),
            rtc_count=6,
            epoch=280.0,
            tail="baseline\nPM: suspend entry (s2idle)\nPM: suspend exit\n",
        )
        result = wake.classify(
            "remove",
            before,
            after,
            event_irqs={"usbin-plugin": 40, "usbin-src-change": 41},
            rtc_irq=42,
            request_epoch=100.0,
            alarm_seconds=180,
        )
        self.assertFalse(result["accepted"])
        self.assertTrue(any("RTC IRQ advanced" in error for error in result["errors"]))
        self.assertTrue(any("RTC fallback" in error for error in result["errors"]))

    def test_insert_requires_post_resume_online_state_and_budget(self) -> None:
        before = snapshot(
            "1",
            success=1,
            event_counts=(10, 10),
            rtc_count=5,
            epoch=100.0,
            tail="baseline\n",
        )
        after = snapshot(
            "1",
            success=2,
            event_counts=(11, 10),
            rtc_count=5,
            epoch=125.0,
            tail="baseline\nPM: suspend entry (s2idle)\nPM: suspend exit\n",
        )
        after["psy"]["input_current_limit"] = "100000"
        result = wake.classify(
            "insert",
            before,
            after,
            event_irqs={"usbin-plugin": 40, "usbin-src-change": 41},
            rtc_irq=42,
            request_epoch=100.0,
            alarm_seconds=180,
        )
        self.assertFalse(result["accepted"])
        self.assertTrue(
            any("unexpected pre-test USB online state" in error for error in result["errors"])
        )


if __name__ == "__main__":
    unittest.main()
