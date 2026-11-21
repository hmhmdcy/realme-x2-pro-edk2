from __future__ import annotations

import contextlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


TRIAL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TRIAL_DIR))

import physical_wake_worker as wake  # noqa: E402


WAKE_VERSION = "#517 SMP PREEMPT test"


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
        "version": f"Linux version 4.14-perf (builder@host) {WAKE_VERSION}",
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


class FakeRtcAlarm:
    def __init__(self, *, mismatch_set: bool = False) -> None:
        self.value = ""
        self.writes: list[str] = []
        self.mismatch_set = mismatch_set

    def read_text(self) -> str:
        return self.value

    def write_text(self, value: str) -> int:
        self.writes.append(value)
        if value != "0" and self.mismatch_set:
            self.value = "9999999999"
        else:
            self.value = value
        return len(value)


class FakeSuspendState:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.writes: list[str] = []

    def write_text(self, value: str) -> int:
        self.writes.append(value)
        if self.fail:
            raise OSError("suspend state write failed")
        return len(value)


class PhysicalWakeTests(unittest.TestCase):
    def test_launcher_reads_full_kernel_version_from_manifest(self) -> None:
        launcher = (TRIAL_DIR / "Invoke-PhysicalUsbWake.ps1").read_text()
        self.assertIn("$manifest.kernel_version", launcher)
        self.assertIn("--expected-kernel-version", launcher)
        self.assertNotIn("expected-build-label", launcher)

    def test_launcher_uses_wifi_control_for_both_wake_directions(self) -> None:
        launcher = (TRIAL_DIR / "Invoke-PhysicalUsbWake.ps1").read_text()
        self.assertIn('$Address = "192.168.0.114"', launcher)
        self.assertNotIn('"169.254.42.1"', launcher)

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

    def test_run_recognizes_platform_rtc_irq_name(self) -> None:
        if os.name != "nt":
            self.skipTest("Windows worker runtime test")
        with tempfile.TemporaryDirectory() as temporary:
            temp_path = Path(temporary)
            root = temp_path / "evidence"
            mem_sleep, rtc_wakeup, psy, _ = self._make_run_files(temp_path)
            base = snapshot(
                "0",
                success=1,
                event_counts=(10, 10),
                rtc_count=5,
                epoch=100.0,
                tail="baseline\n",
            )
            base["interrupts"]["rows"][42]["line"] = (
                "42: 5 0 pmic_arb 123 Edge pm8xxx_rtc_alarm"
            )
            saw_rtc = {}

            def capture_rtc(*args, **kwargs):
                saw_rtc["irq"] = kwargs["rtc_irq"]
                return {"accepted": True, "errors": []}

            with self._run_patches(
                root,
                alarm=FakeRtcAlarm(),
                suspend_state=FakeSuspendState(),
                mem_sleep=mem_sleep,
                rtc_wakeup=rtc_wakeup,
                psy=psy,
                snapshots=[base, base, base],
                classify=capture_rtc,
            ):
                self.assertEqual(wake.run(root, "insert", 180, "#523"), 0)
        self.assertEqual(saw_rtc["irq"], 42)

    def test_non_owned_pm_wakeup_irq_is_rejected_in_both_modes(self) -> None:
        for mode, before_online, after_online in (
            ("insert", "0", "1"),
            ("remove", "1", "0"),
        ):
            with self.subTest(mode=mode):
                before = snapshot(
                    before_online,
                    success=1,
                    event_counts=(10, 10),
                    rtc_count=5,
                    epoch=100.0,
                    tail="baseline\n",
                )
                after = snapshot(
                    after_online,
                    success=2,
                    event_counts=(11, 10),
                    rtc_count=5,
                    epoch=125.0,
                    tail=(
                        "baseline\n"
                        "PM: suspend entry (s2idle)\n"
                        "PM: suspend exit\n"
                    ),
                    pm_wakeup_irq="99",
                )
                result = wake.classify(
                    mode,
                    before,
                    after,
                    event_irqs={"usbin-plugin": 40, "usbin-src-change": 41},
                    rtc_irq=42,
                    request_epoch=100.0,
                    alarm_seconds=180,
                )
                self.assertFalse(result["accepted"])
                self.assertFalse(result["pm_wakeup_irq_is_owned_event"])
                self.assertIn(
                    "pm wakeup IRQ '99' is not an owned USB event IRQ",
                    result["errors"],
                )

    def test_dmesg_delta_survives_rolling_tail(self) -> None:
        before_tail = "stable-line\n" * 1667
        inserted = "PM: suspend entry (s2idle)\nPM: suspend exit\n"
        rolled = (before_tail + inserted)[-20_000:]
        self.assertEqual(wake._dmesg_delta(before_tail, rolled), inserted)

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
            pm_wakeup_irq="40",
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

    def test_expected_full_kernel_version_is_exact(self) -> None:
        before = snapshot(
            "0",
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
            expected_kernel_version="#523 SMP PREEMPT test",
        )
        self.assertFalse(result["accepted"])
        self.assertTrue(
            any(
                "expected #523 SMP PREEMPT test build" in error
                for error in result["errors"]
            )
        )
        result = wake.classify(
            "insert",
            before,
            after,
            event_irqs={"usbin-plugin": 40, "usbin-src-change": 41},
            rtc_irq=42,
            request_epoch=100.0,
            alarm_seconds=180,
            expected_kernel_version=WAKE_VERSION + " extra",
        )
        self.assertFalse(result["accepted"])
        self.assertTrue(
            any("expected #517 SMP PREEMPT test extra" in error for error in result["errors"])
        )

    def test_rtc_alarm_readback_mismatch_is_rejected_and_cleared(self) -> None:
        alarm = FakeRtcAlarm(mismatch_set=True)
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            root = temp_path / "evidence"
            mem_sleep, rtc_wakeup, psy, _ = self._make_run_files(temp_path)
            base = snapshot(
                "0",
                success=1,
                event_counts=(10, 10),
                rtc_count=5,
                epoch=100.0,
                tail="baseline\n",
            )
            with self._run_patches(
                root,
                alarm=alarm,
                suspend_state=FakeSuspendState(),
                mem_sleep=mem_sleep,
                rtc_wakeup=rtc_wakeup,
                psy=psy,
                snapshots=[base, base, base],
            ):
                with self.assertRaisesRegex(
                    RuntimeError, "wakealarm readback mismatch"
                ):
                    wake.run(root, "insert", 180, "#523")

        self.assertGreaterEqual(len(alarm.writes), 2)
        self.assertNotEqual(alarm.writes[0], "0")
        self.assertEqual(alarm.writes[-1], "0")
        self.assertEqual(alarm.value, "0")

    def test_suspend_failure_clears_rtc_alarm_in_finally(self) -> None:
        alarm = FakeRtcAlarm()
        suspend_state = FakeSuspendState(fail=True)
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            root = temp_path / "evidence"
            mem_sleep, rtc_wakeup, psy, _ = self._make_run_files(temp_path)
            base = snapshot(
                "0",
                success=1,
                event_counts=(10, 10),
                rtc_count=5,
                epoch=100.0,
                tail="baseline\n",
            )
            with self._run_patches(
                root,
                alarm=alarm,
                suspend_state=suspend_state,
                mem_sleep=mem_sleep,
                rtc_wakeup=rtc_wakeup,
                psy=psy,
                snapshots=[base, base, base],
            ):
                with self.assertRaisesRegex(OSError, "suspend state write failed"):
                    wake.run(root, "insert", 180, "#523")
            failure = json.loads((root / "failure.json").read_text())

        self.assertEqual(suspend_state.writes, ["mem\n"])
        self.assertGreaterEqual(len(alarm.writes), 2)
        self.assertEqual(alarm.writes[-1], "0")
        self.assertEqual(alarm.value, "0")
        self.assertIn("OSError: suspend state write failed", failure["error"])

    def test_successful_resume_clears_rtc_alarm_before_classification(self) -> None:
        alarm = FakeRtcAlarm()
        suspend_state = FakeSuspendState()
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            root = temp_path / "evidence"
            mem_sleep, rtc_wakeup, psy, _ = self._make_run_files(temp_path)
            before = snapshot(
                "0",
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
                tail=(
                    "baseline\n"
                    "PM: suspend entry (s2idle)\n"
                    "PM: suspend exit\n"
                ),
                pm_wakeup_irq="40",
            )

            def classify_after_cleanup(*args, **kwargs):
                self.assertEqual(alarm.value, "0")
                return {"accepted": True, "errors": []}

            with self._run_patches(
                root,
                alarm=alarm,
                suspend_state=suspend_state,
                mem_sleep=mem_sleep,
                rtc_wakeup=rtc_wakeup,
                psy=psy,
                snapshots=[before, before, after],
                classify=classify_after_cleanup,
            ):
                self.assertEqual(wake.run(root, "insert", 180, "#523"), 0)

            terminal = json.loads((root / "terminal.json").read_text())
            result = json.loads((root / "result.json").read_text())

        self.assertEqual(suspend_state.writes, ["mem\n"])
        self.assertEqual(alarm.writes[-1], "0")
        self.assertTrue(terminal["accepted"])
        self.assertTrue(result["accepted"])

    def test_wake_run_paths_add_guid_and_reject_existing_nonempty_directory(
        self,
    ) -> None:
        if os.name != "nt":
            self.skipTest("Windows PowerShell launcher test")
        powershell = shutil.which("powershell.exe") or shutil.which("pwsh")
        self.assertIsNotNone(powershell, "PowerShell is required for launcher test")
        launcher = TRIAL_DIR / "Invoke-PhysicalUsbWake.ps1"
        with tempfile.TemporaryDirectory() as temp:
            output_root = Path(temp) / "output"
            env = os.environ.copy()
            env.update(
                {
                    "WAKE_SCRIPT": str(launcher),
                    "WAKE_OUTPUT_ROOT": str(output_root),
                }
            )
            command = r"""
$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile(
    $env:WAKE_SCRIPT,
    [ref]$tokens,
    [ref]$parseErrors
)
if ($parseErrors.Count -ne 0) {
    throw ($parseErrors | ForEach-Object { $_.Message }) -join "; "
}
$function = $ast.Find({
    param($node)
    $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
        $node.Name -eq "New-WakeRunPaths"
}, $true)
if (-not $function) {
    throw "New-WakeRunPaths was not found"
}
Invoke-Expression $function.Extent.Text
$first = New-WakeRunPaths `
    -Mode insert `
    -OutputRoot $env:WAKE_OUTPUT_ROOT `
    -RemoteRoot "/root/charging-management-20261023"
Set-Content -LiteralPath (Join-Path $first.Local "sentinel.txt") -Value "x"
$rejected = $false
try {
    New-WakeRunPaths `
        -Mode insert `
        -OutputRoot $env:WAKE_OUTPUT_ROOT `
        -RemoteRoot "/root/charging-management-20261023" `
        -RunId $first.RunId | Out-Null
} catch {
    $rejected = $_.Exception.Message -like "*wake output directory is not empty*"
}
if (-not $rejected) {
    throw "existing non-empty output directory was not rejected"
}
Write-Output $first.RunId
"""
            completed = subprocess.run(
                [powershell, "-NoProfile", "-NonInteractive", "-Command", command],
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
                check=False,
            )
        self.assertEqual(
            completed.returncode,
            0,
            f"stdout={completed.stdout}\nstderr={completed.stderr}",
        )
        run_id = completed.stdout.strip().splitlines()[-1]
        self.assertRegex(
            run_id,
            re.compile(
                r"^physical-usb-wake-insert-[0-9]{8}-[0-9]{6}-[0-9a-f]{32}$"
            ),
        )

    def test_launcher_rejects_existing_remote_directory(self) -> None:
        launcher = (TRIAL_DIR / "Invoke-PhysicalUsbWake.ps1").read_text()
        self.assertIn("mkdir -p '$remoteParent' && mkdir '$remote'", launcher)
        self.assertNotIn("mkdir -p '$remote'", launcher)

    def test_launcher_uploads_worker_common_dependency(self) -> None:
        launcher = (TRIAL_DIR / "Invoke-PhysicalUsbWake.ps1").read_text()
        self.assertTrue(launcher.startswith("#requires -Version 7.0\n"))
        self.assertIn("[string]$WorkerPath,", launcher)
        self.assertIn("[string]$CommonPath,", launcher)
        self.assertIn(
            'if (-not $WorkerPath) {\n'
            '    $WorkerPath = Join-Path $PSScriptRoot "physical_wake_worker.py"\n'
            '}',
            launcher,
        )
        self.assertIn(
            'if (-not $CommonPath) {\n'
            '    $CommonPath = Join-Path $PSScriptRoot "trial_common.py"\n'
            '}',
            launcher,
        )
        self.assertNotIn('[string]$CommonPath = (Join-Path $PSScriptRoot', launcher)
        self.assertIn('${target}:$remote/trial_common.py', launcher)

    def _make_run_files(
        self, root: Path
    ) -> tuple[Path, Path, Path, Path]:
        mem_sleep = root / "mem_sleep"
        mem_sleep.write_text("[s2idle]")
        rtc_wakeup = root / "rtc-wakeup"
        rtc_wakeup.write_text("enabled")
        psy = root / "psy"
        (psy / "power").mkdir(parents=True)
        (psy / "power" / "wakeup").write_text("enabled")
        boot_id = root / "boot-id"
        boot_id.write_text("boot-1")
        return mem_sleep, rtc_wakeup, psy, boot_id

    def _run_patches(
        self,
        root: Path,
        *,
        alarm: FakeRtcAlarm,
        suspend_state: FakeSuspendState,
        mem_sleep: Path,
        rtc_wakeup: Path,
        psy: Path,
        snapshots: list[dict],
        classify=None,
    ):
        boot_id = mem_sleep.parent / "boot-id"
        snapshot_values = iter(snapshots)

        def fake_snapshot() -> dict:
            if not (root / "go.json").exists():
                root.mkdir(parents=True, exist_ok=True)
                (root / "go.json").write_text('{"boot_id": "boot-1"}\n')
            return next(snapshot_values)

        def fake_atomic_json(path: Path, value: object) -> None:
            path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")

        patches = [
            mock.patch.object(wake, "PSY", psy),
            mock.patch.object(wake, "MEM_SLEEP", mem_sleep),
            mock.patch.object(wake, "SUSPEND_STATE", suspend_state),
            mock.patch.object(wake, "RTC_WAKEALARM", alarm),
            mock.patch.object(wake, "RTC_WAKEUP", rtc_wakeup),
            mock.patch.object(wake, "BOOT_ID", boot_id),
            mock.patch.object(wake, "PRE_SUSPEND_DELAY_SECONDS", 0),
            mock.patch.object(wake, "_snapshot", side_effect=fake_snapshot),
            mock.patch.object(
                wake,
                "_find_event_irqs",
                return_value={"usbin-plugin": 40, "usbin-src-change": 41},
            ),
            mock.patch.object(
                wake, "_atomic_json", side_effect=fake_atomic_json
            ),
            mock.patch.object(wake.os, "geteuid", return_value=0, create=True),
        ]
        if classify is not None:
            patches.append(mock.patch.object(wake, "classify", side_effect=classify))

        stack = contextlib.ExitStack()
        for patcher in patches:
            stack.enter_context(patcher)
        return stack


if __name__ == "__main__":
    unittest.main()
