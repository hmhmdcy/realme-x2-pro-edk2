"""Run real transaction implementation against fake OS/sysfs boundaries."""
from pathlib import Path
import errno
import hashlib
import importlib.util
import json
import subprocess
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('pm_transaction', ROOT / 'pm-transaction.py')
pm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pm)


class FakeOS:
    def __init__(self):
        self.mono = self.boot = self.rtc_elapsed = 0.0
        self.alarm = None
        self.irq = 4
        self.count = 10
        self.trace = []
        self.sync_delay = self.count_delay = 0
        self.on_phase = None
        self.fail = {}
        self.mem_calls = self.actual_sleeps = 0
        self.count_reads = []
        self.accepted_count = None
        self.after_handshake = None
        self.partial_arm = False

    def advance(self, seconds, awake=True):
        self.rtc_elapsed += seconds
        self.boot += seconds
        if awake:
            self.mono += seconds
        if self.alarm is not None and self.alarm <= 1000 + self.rtc_elapsed:
            self.alarm = None
            self.irq += 1
            self.count += 1

    def operation(self, name):
        self.trace.append(name)
        if name in self.fail:
            error = self.fail[name]
            if isinstance(error, list):
                error = error.pop(0) if error else None
            if error:
                raise error

    def phase(self, entry):
        self.operation('phase:' + entry['phase'])
        if self.on_phase:
            self.on_phase(entry['phase'], self)

    def monotonic(self):
        return self.mono

    def boottime(self):
        return self.boot

    def read_alarm(self):
        self.operation('read_alarm')
        return self.alarm

    def read_rtc_epoch(self):
        self.operation('read_epoch')
        return 1000 + int(self.rtc_elapsed)

    def read_rtc_irq(self):
        self.operation('read_irq')
        return self.irq

    def sync(self):
        self.operation('sync')
        self.advance(self.sync_delay)

    def read_wakeup_count(self, timeout):
        self.operation('read_count')
        assert self.alarm is None, 'count read must precede arm'
        if self.count_delay > timeout:
            self.advance(timeout)
            raise TimeoutError(errno.ETIMEDOUT, 'simulated in_progress timeout')
        self.advance(self.count_delay)
        self.count_reads.append(self.count)
        return self.count

    def write_alarm(self, target):
        self.operation('clear_alarm' if target == 0 else 'write_alarm')
        self.alarm = target or None
        if self.partial_arm and target:
            raise OSError(errno.EIO, 'partial alarm write installed target')

    def write_wakeup_count(self, count):
        self.operation('write_count')
        assert self.count_reads == [count], 'must write original count, never reread'
        if count != self.count:
            raise OSError(errno.EINVAL, 'wakeup count changed')
        self.accepted_count = count
        if self.after_handshake:
            self.after_handshake(self)

    def suspend_to_mem(self):
        self.operation('mem')
        self.mem_calls += 1
        # Model the current kernel's pm_wakeup_pending check after handshake.
        if self.count != self.accepted_count:
            return
        self.actual_sleeps += 1
        assert self.alarm is not None
        self.advance(self.alarm - (1000 + self.rtc_elapsed), awake=False)
        self.advance(.1)


class TransactionTests(unittest.TestCase):
    def run_once(self, io, **kwargs):
        result = pm.suspend_once(io, **kwargs)
        self.assertLessEqual(result['mem_write_attempts'], 1)
        self.assertLessEqual(io.mem_calls, 1)
        self.assertFalse(result['whole_device_pm_acceptance'])
        return result

    def assert_aborted(self, io, **kwargs):
        result = self.run_once(io, **kwargs)
        self.assertEqual(result['outcome'], 'aborted')
        self.assertEqual(result['mem_write_attempts'], 0)
        self.assertEqual(io.actual_sleeps, 0)
        return result

    def test_normal_single_transaction(self):
        io = FakeOS()
        result = self.run_once(io)
        self.assertEqual(result['outcome'], 'returned')
        self.assertEqual(io.actual_sleeps, 1)
        self.assertEqual(result['cleanup'], 'alarm_already_consumed_or_cleared')
        self.assertAlmostEqual(result['estimated_residency_seconds'], 15)
        self.assertLess(io.trace.index('sync'), io.trace.index('read_count'))
        self.assertLess(io.trace.index('read_count'), io.trace.index('write_alarm'))
        self.assertEqual(io.trace[io.trace.index('write_count') + 1], 'mem')

    def test_long_sync_finishes_before_arm(self):
        io = FakeOS(); io.sync_delay = 35
        result = self.run_once(io)
        self.assertEqual(result['sync_seconds'], 35)
        self.assertEqual(result['alarm_target'], 1050)
        self.assertAlmostEqual(result['estimated_residency_seconds'], 15)

    def test_wait_for_in_progress_occurs_before_alarm(self):
        io = FakeOS(); io.count_delay = 20
        result = self.run_once(io, wakeup_count_timeout_seconds=25)
        self.assertEqual(result['wakeup_count_read_seconds'], 20)
        self.assertEqual(result['alarm_target'], 1035)
        self.assertEqual(io.actual_sleeps, 1)

    def test_in_progress_wait_timeout_never_arms(self):
        io = FakeOS(); io.count_delay = 20
        result = self.assert_aborted(io)
        self.assertEqual(result['error']['errno'], errno.ETIMEDOUT)
        self.assertNotIn('write_alarm', io.trace)

    def test_existing_alarm_preserved(self):
        io = FakeOS(); io.alarm = 1200
        result = self.assert_aborted(io)
        self.assertEqual(io.alarm, 1200)
        self.assertEqual(result['cleanup'], 'not_owned')
        self.assertNotIn('sync', io.trace)

    def test_alarm_appears_during_count_wait(self):
        io = FakeOS()
        io.on_phase = lambda phase, fake: setattr(fake, 'alarm', 1300) if phase == 'wakeup_count_read_complete' else None
        self.assert_aborted(io)
        self.assertEqual(io.alarm, 1300)
        self.assertNotIn('write_alarm', io.trace)

    def test_expiry_during_phase_logging_is_detected(self):
        io = FakeOS()
        io.on_phase = lambda phase, fake: fake.advance(16) if phase == 'entering_mem' else None
        result = self.assert_aborted(io)
        self.assertEqual(io.irq, 5)
        self.assertNotIn('write_count', io.trace)
        self.assertEqual(result['cleanup'], 'alarm_already_consumed_or_cleared')

    def test_insufficient_remaining_time_cancels_own_alarm(self):
        io = FakeOS()
        io.on_phase = lambda phase, fake: fake.advance(11) if phase == 'entering_mem' else None
        result = self.assert_aborted(io)
        self.assertEqual(result['pre_mem']['remaining_lower_bound_seconds'], 3)
        self.assertEqual(result['cleanup'], 'owned_alarm_cancelled')
        self.assertIsNone(io.alarm)

    def test_rtc_irq_change_aborts_without_mem(self):
        io = FakeOS()
        io.on_phase = lambda phase, fake: setattr(fake, 'irq', 5) if phase == 'entering_mem' else None
        result = self.assert_aborted(io)
        self.assertEqual(result['pre_mem']['rtc_irq_delta'], 1)
        self.assertEqual(result['cleanup'], 'owned_alarm_cancelled')

    def test_count_change_handshake_rejected(self):
        io = FakeOS()
        io.on_phase = lambda phase, fake: setattr(fake, 'count', 11) if phase == 'alarm_armed' else None
        result = self.assert_aborted(io)
        self.assertEqual(result['error']['errno'], errno.EINVAL)
        self.assertEqual(result['cleanup'], 'owned_alarm_cancelled')

    def test_no_new_count_read_after_arm(self):
        io = FakeOS()
        self.run_once(io)
        self.assertEqual(io.trace.count('read_count'), 1)
        self.assertEqual(io.count_reads, [10])
        self.assertEqual(io.accepted_count, 10)

    def test_other_owner_replaces_alarm(self):
        io = FakeOS()
        io.on_phase = lambda phase, fake: setattr(fake, 'alarm', 1400) if phase == 'entering_mem' else None
        result = self.assert_aborted(io)
        self.assertEqual(io.alarm, 1400)
        self.assertEqual(result['cleanup'], 'changed_alarm_preserved')
        self.assertNotIn('clear_alarm', io.trace)

    def test_partial_arm_still_cleans_installed_target(self):
        io = FakeOS(); io.partial_arm = True
        result = self.assert_aborted(io)
        self.assertEqual(result['error']['errno'], errno.EIO)
        self.assertEqual(result['cleanup'], 'owned_alarm_cancelled')
        self.assertIsNone(io.alarm)

    def test_each_io_error_before_mem_cancels_safely(self):
        for method in ['sync', 'read_count', 'write_alarm', 'read_epoch', 'read_irq', 'write_count']:
            with self.subTest(method=method):
                io = FakeOS(); io.fail[method] = OSError(errno.EIO, method)
                result = self.assert_aborted(io)
                self.assertEqual(result['error']['errno'], errno.EIO)
                self.assertNotEqual(result['cleanup'], 'unknown_or_failed')

    def test_phase_log_failure_after_arm_cancels(self):
        io = FakeOS(); io.fail['phase:entering_mem'] = OSError(errno.ENOSPC, 'log full')
        result = self.assert_aborted(io)
        self.assertEqual(result['cleanup'], 'owned_alarm_cancelled')

    def test_mem_write_error_is_not_retried(self):
        io = FakeOS(); io.fail['mem'] = OSError(errno.EBUSY, 'PM refused')
        result = self.run_once(io)
        self.assertEqual(result['outcome'], 'failed')
        self.assertEqual(result['mem_write_attempts'], 1)
        self.assertFalse(result['mem_returned'])
        self.assertEqual(io.trace.count('mem'), 1)
        self.assertEqual(result['cleanup'], 'owned_alarm_cancelled')

    def test_kernel_detects_event_after_accepted_handshake(self):
        io = FakeOS(); io.after_handshake = lambda fake: fake.advance(16)
        result = self.run_once(io)
        self.assertEqual(result['outcome'], 'returned')
        self.assertEqual(io.actual_sleeps, 0)
        self.assertEqual(result['estimated_residency_seconds'], 0)
        self.assertFalse(result['whole_device_pm_acceptance'])

    def test_cleanup_failure_is_reported(self):
        io = FakeOS()
        io.on_phase = lambda phase, fake: fake.advance(11) if phase == 'entering_mem' else None
        io.fail['clear_alarm'] = OSError(errno.EIO, 'clear failed')
        result = self.assert_aborted(io)
        self.assertEqual(result['cleanup'], 'unknown_or_failed')
        self.assertEqual(result['cleanup_error']['errno'], errno.EIO)

    def test_keyboard_interrupt_still_cleans_owned_alarm(self):
        io = FakeOS(); io.fail['phase:entering_mem'] = KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            pm.suspend_once(io)
        self.assertIsNone(io.alarm)
        self.assertEqual(io.mem_calls, 0)

    def test_bad_config_has_no_io(self):
        for arguments in [{'alarm_delay_seconds': 1}, {'minimum_remaining_seconds': 0},
                          {'alarm_delay_seconds': True}, {'wakeup_count_timeout_seconds': 0},
                          {'wakeup_count_timeout_seconds': float('inf')},
                          {'wakeup_count_timeout_seconds': float('nan')},
                          {'wakeup_count_timeout_seconds': True}]:
            with self.subTest(arguments=arguments):
                io = FakeOS()
                with self.assertRaises(ValueError):
                    pm.suspend_once(io, **arguments)
                self.assertEqual(io.trace, [])


class RealAdapterBoundaryTests(unittest.TestCase):
    def test_single_sysfs_write_and_close(self):
        with patch.object(pm.os, 'open', return_value=7) as opening, patch.object(pm.os, 'write', return_value=3) as writing, patch.object(pm.os, 'close') as closing:
            pm.SysfsPMIO._single_write('/fake/state', b'mem')
        self.assertEqual(opening.call_count, 1)
        writing.assert_called_once_with(7, b'mem')
        closing.assert_called_once_with(7)

    def test_short_sysfs_write_never_continues(self):
        with patch.object(pm.os, 'open', return_value=7), patch.object(pm.os, 'write', return_value=1) as writing, patch.object(pm.os, 'close') as closing:
            with self.assertRaises(OSError) as error:
                pm.SysfsPMIO._single_write('/fake/state', b'mem')
        self.assertEqual(error.exception.errno, errno.EIO)
        writing.assert_called_once_with(7, b'mem')
        closing.assert_called_once_with(7)

    def test_sysfs_write_error_closes_once(self):
        with patch.object(pm.os, 'open', return_value=7), patch.object(pm.os, 'write', side_effect=OSError(errno.EIO, 'write failed')) as writing, patch.object(pm.os, 'close') as closing:
            with self.assertRaises(OSError):
                pm.SysfsPMIO._single_write('/fake/state', b'mem')
        self.assertEqual(writing.call_count, 1)
        closing.assert_called_once_with(7)

    def test_count_reader_has_explicit_process_timeout(self):
        io = pm.SysfsPMIO(lambda _: None)
        response = subprocess.CompletedProcess([], 0, b'123\n', b'')
        with patch.object(pm.subprocess, 'run', return_value=response) as running:
            self.assertEqual(io.read_wakeup_count(3.5), 123)
        self.assertEqual(running.call_args.kwargs['timeout'], 3.5)
        self.assertEqual(running.call_args.args[0][-1], '/sys/power/wakeup_count')

    def test_count_reader_timeout_propagates_before_arm(self):
        io = pm.SysfsPMIO(lambda _: None)
        with patch.object(pm.subprocess, 'run', side_effect=subprocess.TimeoutExpired(['reader'], 3)):
            with self.assertRaises(TimeoutError) as error:
                io.read_wakeup_count(3)
        self.assertEqual(error.exception.errno, errno.ETIMEDOUT)

    def test_count_reader_invalid_or_failed_response(self):
        io = pm.SysfsPMIO(lambda _: None)
        for response in [subprocess.CompletedProcess([], 1, b'', b'failure'),
                         subprocess.CompletedProcess([], 0, b'not-a-count\n', b'')]:
            with self.subTest(response=response), patch.object(pm.subprocess, 'run', return_value=response):
                with self.assertRaises((OSError, ValueError)):
                    io.read_wakeup_count(3)

    def test_rtc_irq_cpu_count_not_hardcoded(self):
        io = pm.SysfsPMIO(lambda _: None)
        for line, total in [('99: 1 2 GICv3 44 Level pm8xxx_rtc_alarm\n', 3),
                            ('99: 0 1 2 3 4 5 6 7 GICv3 44 pm8xxx_rtc_alarm\n', 28)]:
            with self.subTest(line=line), patch.object(Path, 'read_text', return_value=line):
                self.assertEqual(io.read_rtc_irq(), total)


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromModule(__import__(__name__))
    count = suite.countTestCases()
    run = unittest.TextTestRunner(verbosity=1).run(suite)
    result = {'passed': run.wasSuccessful(), 'test_methods': count,
              'scope': 'actual suspend_once implementation and real adapter at simulated OS boundaries; no phone or PM acceptance',
              'tested_files': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                               for name in ['pm-transaction.py', 'test-pm-transaction.py']}}
    (ROOT / 'pm-transaction-test-result.json').write_text(json.dumps(result, indent=2) + '\n')
    raise SystemExit(0 if result['passed'] else 1)
