"""Control/cleanup tests, not hardware or host-enumeration evidence."""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import tempfile
import types
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('budget_cycle', HERE / 'usb-budget-cycle.py')
cycle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cycle)
BASE = dict(native_online=1, native_type='SDP', native_max=500000, native_input=500000,
            tcpm_online=1, tcpm_type='C', tcpm_max=500000, tcpm_now=500000,
            tcpm_voltage=5000000, udc='configured',
            roles=dict(power_role='sink', data_role='device', power_operation_mode='default'))


class Control(unittest.TestCase):
    def run_case(self, mode='good'):
        stamp, actions, phase, rows = [0.0], [], ['initial'], []

        def write(action):
            actions.append(action)
            phase[0] = action
            if mode == 'disconnect-write-error' and action == 'disconnect':
                raise OSError('partial disconnect write')
            if mode == 'connect-write-error' and action == 'connect':
                raise OSError('connect error')

        def read():
            if mode == 'read-error' and phase[0] == 'disconnect':
                raise OSError('read error')
            row = copy.deepcopy(BASE)
            if phase[0] == 'disconnect':
                row.update(udc='not attached', native_max=0, native_input=0, tcpm_max=0, tcpm_now=0)
                if mode == 'stale-tcpm':
                    row.update(tcpm_max=500000, tcpm_now=500000)
                if mode == 'still-configured':
                    row['udc'] = 'configured'
                if mode == 'physical-source-lost':
                    row['native_online'] = 0
                if mode == 'PD':
                    row['tcpm_type'] = 'PD'
            elif mode == 'reconnect-budget100':
                row.update(native_max=100000, native_input=100000, tcpm_max=100000, tcpm_now=100000)
            elif mode == 'connect-write-error':
                row.update(udc='not attached', native_max=0, native_input=0, tcpm_max=0, tcpm_now=0)
            return row

        def record(phase_name, row):
            if mode == 'record-error' and phase_name == 'disconnected':
                raise OSError('sample log full')
            rows.append((phase_name, row))

        def sleep(amount):
            stamp[0] += amount

        return cycle.exercise(read, write, lambda: stamp[0], sleep, record), actions, rows, stamp[0]

    def test_zero_then_real500(self):
        result, actions, rows, duration = self.run_case()
        self.assertTrue(result['passed'])
        self.assertEqual(actions, ['disconnect', 'connect'])
        self.assertGreaterEqual(duration, 1.25)

    def test_partial_disconnect_still_reconnects(self):
        result, actions, _, _ = self.run_case('disconnect-write-error')
        self.assertFalse(result['passed'])
        self.assertTrue(result['reconnect_observed'])
        self.assertEqual(actions, ['disconnect', 'connect'])

    def test_read_and_log_errors_still_reconnect(self):
        for mode in ['read-error', 'record-error']:
            with self.subTest(mode=mode):
                result, actions, _, _ = self.run_case(mode)
                self.assertFalse(result['passed'])
                self.assertTrue(result['reconnect_observed'])
                self.assertEqual(actions, ['disconnect', 'connect'])

    def test_false_disconnect_cases_rejected_and_recovered(self):
        for mode in ['stale-tcpm', 'still-configured', 'physical-source-lost', 'PD']:
            with self.subTest(mode=mode):
                result, actions, _, duration = self.run_case(mode)
                self.assertFalse(result['passed'])
                self.assertFalse(result['disconnect_observed'])
                self.assertTrue(result['reconnect_observed'])
                self.assertEqual(actions, ['disconnect', 'connect'])
                self.assertLessEqual(duration, 6.25)

    def test_stale100_is_not_recovered500(self):
        result, actions, _, duration = self.run_case('reconnect-budget100')
        self.assertFalse(result['passed'])
        self.assertFalse(result['reconnect_observed'])
        self.assertLessEqual(duration, 30.25)

    def test_connect_write_error_is_failure(self):
        result, actions, _, duration = self.run_case('connect-write-error')
        self.assertFalse(result['passed'])
        self.assertIsNotNone(result['reconnect_error'])
        self.assertEqual(actions, ['disconnect', 'connect'])
        self.assertLessEqual(duration, 30.25)


class IndependentRecovery(unittest.TestCase):
    def case(self, scenario):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'state').write_text('not attached\n')
            (root / 'soft_connect').write_text('untouched\n')
            if scenario == 'returned':
                (root / 'reconnect-returned.json').write_text('{}')
            if scenario == 'configured':
                (root / 'state').write_text('configured\n')
            actual_boot = 'next-boot' if scenario == 'boot-ended' else 'trial-boot'
            with patch.object(cycle, 'RUN', root), patch.object(cycle, 'UDC', root), \
                 patch.object(cycle.time, 'sleep'), patch.object(cycle, 'boot', return_value=actual_boot), \
                 patch.object(cycle.os, 'uname', return_value=types.SimpleNamespace(version=cycle.VERSION)):
                cycle.recover('trial-boot')
            return json.loads((root / 'recovery-terminal.json').read_bytes()), (root / 'soft_connect').read_text()

    def test_abandoned_disconnect_gets_connect(self):
        result, value = self.case('abandoned')
        self.assertTrue(result['write_attempted'])
        self.assertEqual(value, 'connect\n')
        self.assertIsNone(result['error'])

    def test_no_duplicate_connect_or_cross_boot_write(self):
        for scenario in ['returned', 'configured', 'boot-ended']:
            with self.subTest(scenario=scenario):
                result, value = self.case(scenario)
                self.assertFalse(result['write_attempted'])
                self.assertEqual(value, 'untouched\n')


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromModule(__import__(__name__))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    proof = dict(passed=result.wasSuccessful(), test_methods=result.testsRun,
                 hardware_tested=False, host_enumeration_tested=False,
                 worker_sha256=hashlib.sha256((HERE / 'usb-budget-cycle.py').read_bytes()).hexdigest(),
                 test_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (HERE / 'usb-cycle-test-result.json').write_text(json.dumps(proof, indent=2) + '\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
