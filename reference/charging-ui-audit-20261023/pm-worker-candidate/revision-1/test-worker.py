"""Tests actual dispatch/classification functions; never constructs live IO."""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import os
import subprocess
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('candidate_worker', ROOT / 'worker.py')
worker = importlib.util.module_from_spec(spec); spec.loader.exec_module(worker)


def config():
    return {'execute': True, 'window_confirmed': True, 'transaction': 'charging-pm-r6-candidate',
            'boot_id': '12345678-1234-4234-8234-123456789abc', 'release': 'reviewed-kernel',
            'manifest_sha256': 'a' * 64, 'live_sha256': 'b' * 64, 'previous_receipt_sha256': 'c' * 64,
            'output_root': str(ROOT / 'unused-test-output'), 'live_helper': '/unused-live', 'previous_receipt': '/unused-receipt'}


def snapshot(c):
    return {'boot_id': c['boot_id'], 'release': c['release'], 'manifest_sha256': c['manifest_sha256'],
            'state': {'taint': '0', 'driver': 'samurai-mp2650', 'camera_pm': {n: 'suspended' for n in worker.CAMERA},
                      'm2m': json.dumps({'users': 0, 'running': False, 'fatal': False, 'pinned': False, 'orphans': 0, 'first_error': 0}),
                      'services': [{'comm': n, 'pid': i + 100, 'uid': 10000} for i, n in enumerate(worker.SERVICES)],
                      'registers': {'00': 2, '02': 5, '13': 27}},
            'sample': {'valid': 1, 'online': 1, 'protection_ok': 1, 'desired_enable': 1, 'shadow': 0,
                       'age_ms': 20, 'budget_ua': 100000, 'error': 0, 'stop_error': 0, 'latched': 0, 'source_inhibit': 0, 'fault': 0},
            'stats': {'success': 3, 'fail': 0, 'failed_suspend': 0}, 'rtc_irq': 10, 'rtc_irq_number': 88,
            'wakeup_irq': None, 'modules_exact': True, 'read_only_prerequisites': True,
            'previous': {'receipt_valid': True, 'process_state': 'absent'}, 'allowance': 100000, 'dmesg': 'baseline\n'}


def trace():
    drivers = [('0-005c', 'samurai-mp2650'), ('samurai-usb-input', 'samurai-usb-input'),
               ('samurai-gauge-protection', 'samurai-gauge-protection'), ('5-0055', 'bq27xxx-battery')]
    rows = ['# entries-in-buffer/entries-written: 16/16 #P:8']
    for phase, ordered, base in [('suspend', drivers, 1), ('resume', list(reversed(drivers)), 2)]:
        for i, (device, driver) in enumerate(ordered):
            when = base + i / 5
            rows += [f' x [000] ... {when:.3f}: device_pm_callback_start: {driver} {device}, parent: bus, driver [{phase}]',
                     f' x [000] ... {when + .01:.3f}: device_pm_callback_end: {driver} {device}, err=0']
    return '\n'.join(rows)


class FakeBoard:
    def __init__(self, c):
        self.before = snapshot(c); self.after = copy.deepcopy(self.before)
        self.after.update(rtc_irq=11, wakeup_irq=88, dmesg='baseline\nresume\n')
        self.after['stats']['success'] = 4
        self.primitive = {'outcome': 'returned', 'mem_returned': True,
                          'cleanup': 'alarm_already_consumed_or_cleared', 'estimated_residency_seconds': 15}
        self.text = trace(); self.cleanup = {'passed': True, 'owned': True}
        self.saved = {}; self.calls = []; self.owned = False; self.fail = {}

    def call(self, name):
        self.calls.append(name)
        if name in self.fail:
            raise self.fail[name]

    def create_new(self, c): self.call('create')
    def save(self, name, data): self.saved[name] = copy.deepcopy(data)
    def capture(self, c, before):
        self.call('capture_before' if before else 'capture_after')
        return copy.deepcopy(self.before if before else self.after)
    def start_trace(self, c): self.owned = True; self.call('start_trace')
    def suspend_once(self): self.call('primitive'); return copy.deepcopy(self.primitive)
    def finish_trace(self): self.call('finish_trace'); self.owned = False; return self.text, self.cleanup
    def wait_for_fresh_sample(self): self.call('wait')
    def cleanup_trace_if_owned(self):
        self.calls.append('cleanup')
        if self.owned:
            self.owned = False
            return self.cleanup


class DispatchTests(unittest.TestCase):
    def test_success_requires_all_evidence(self):
        c = config(); board = FakeBoard(c)
        result = worker.dispatch(c, board)
        self.assertTrue(result['passed'])
        self.assertEqual(board.calls.count('primitive'), 1)
        self.assertEqual(result['classification'], 'verified')
        self.assertEqual(board.calls[:4], ['create', 'capture_before', 'start_trace', 'primitive'])

    def test_execute_or_window_missing_causes_no_board_io(self):
        for name in ['execute', 'window_confirmed']:
            c = config(); c[name] = False; board = FakeBoard(c)
            with self.assertRaises(ValueError): worker.dispatch(c, board)
            self.assertEqual(board.calls, [])

    def test_existing_transaction_is_never_reused(self):
        c = config(); board = FakeBoard(c); board.fail['create'] = FileExistsError()
        with self.assertRaises(FileExistsError): worker.dispatch(c, board)
        self.assertEqual(board.calls, ['create']); self.assertEqual(board.saved, {})

    def test_old_r5_name_rejected(self):
        c = config(); c['transaction'] = 'charging-pm-r5'; board = FakeBoard(c)
        with self.assertRaises(ValueError): worker.dispatch(c, board)
        self.assertEqual(board.calls, [])

    def test_preflight_identity_and_previous_rejections_do_not_start_trace(self):
        for key, value in [('boot_id', 'other'), ('manifest_sha256', 'f' * 64), ('modules_exact', False),
                           ('previous', {'receipt_valid': False, 'process_state': 'absent'}),
                           ('previous', {'receipt_valid': True, 'process_state': 'same_worker_alive'}),
                           ('previous', {'receipt_valid': True, 'process_state': 'unknown'})]:
            with self.subTest(key=key, value=value):
                c = config(); board = FakeBoard(c); board.before[key] = value
                result = worker.dispatch(c, board)
                self.assertFalse(result['passed']); self.assertEqual(result['classification'], 'preflight_rejected')
                self.assertNotIn('start_trace', board.calls); self.assertNotIn('primitive', board.calls)
                self.assertFalse(board.saved['preflight-result.json']['passed'])

    def test_preflight_read_failure_is_distinct(self):
        c = config(); board = FakeBoard(c); board.fail['capture_before'] = OSError('identity unreadable')
        result = worker.dispatch(c, board)
        self.assertEqual(result['classification'], 'preflight_evidence_failed')
        self.assertNotIn('primitive', board.calls)

    def test_primitive_aborted_retained_as_independent_result(self):
        c = config(); board = FakeBoard(c)
        board.primitive = {'outcome': 'aborted', 'mem_returned': False, 'cleanup': 'owned_alarm_cancelled', 'error': {'errno': 22}}
        result = worker.dispatch(c, board)
        self.assertFalse(result['passed']); self.assertEqual(result['classification'], 'primitive_aborted_or_failed')
        self.assertEqual(board.saved['primitive-result.json'], board.primitive)
        self.assertNotIn('wait', board.calls)

    def test_primitive_exception_and_trace_cleanup_retained(self):
        c = config(); board = FakeBoard(c); board.fail['primitive'] = RuntimeError('unexpected')
        result = worker.dispatch(c, board)
        self.assertFalse(result['passed']); self.assertIn('primitive-exception.json', board.saved)
        self.assertIn('trace-cleanup-final.json', board.saved)

    def test_interrupt_retains_failure_stage_and_trace_cleanup(self):
        c = config(); board = FakeBoard(c); board.fail['primitive'] = KeyboardInterrupt()
        result = worker.dispatch(c, board)
        self.assertFalse(result['passed']); self.assertEqual(result['failed_stage'], 'primitive')
        self.assertEqual(board.saved['primitive-exception.json']['type'], 'KeyboardInterrupt')
        self.assertIn('trace-cleanup-final.json', board.saved)

    def test_partial_trace_setup_failure_never_calls_pm(self):
        c = config(); board = FakeBoard(c); board.fail['start_trace'] = OSError('trace event missing')
        result = worker.dispatch(c, board)
        self.assertFalse(result['passed']); self.assertNotIn('primitive', board.calls)
        self.assertIn('trace-cleanup-final.json', board.saved)

    def test_returned_without_sleep_cannot_pass(self):
        c = config(); board = FakeBoard(c); board.primitive['estimated_residency_seconds'] = 0
        result = worker.dispatch(c, board)
        self.assertFalse(result['passed']); self.assertFalse(result['checks']['actual_residency'])

    def test_other_or_unknown_wakeup_irq_cannot_pass(self):
        for irq in [None, 89, '88']:
            c = config(); board = FakeBoard(c); board.after['wakeup_irq'] = irq
            result = worker.dispatch(c, board)
            self.assertFalse(result['passed']); self.assertFalse(result['checks']['rtc_was_wakeup_irq'])

    def test_missing_stats_trace_health_or_cleanup_cannot_pass(self):
        mutations = [lambda b: b.after.update(stats={}), lambda b: setattr(b, 'text', ''),
                     lambda b: b.after['sample'].update(valid=0),
                     lambda b: setattr(b, 'cleanup', {'passed': False, 'errors': ['rmdir failed']}),
                     lambda b: b.primitive.update(cleanup='unknown_or_failed', cleanup_error={'errno': 5}),
                     lambda b: b.after.update(dmesg='truncated ring\n'),
                     lambda b: b.after.update(dmesg=b.before['dmesg'] + 'WARNING: new\n')]
        for mutate in mutations:
            c = config(); board = FakeBoard(c); mutate(board)
            self.assertFalse(worker.dispatch(c, board)['passed'])

    def test_post_capture_error_does_not_erase_primitive(self):
        c = config(); board = FakeBoard(c); board.fail['capture_after'] = OSError('USB unavailable')
        result = worker.dispatch(c, board)
        self.assertFalse(result['passed']); self.assertIn('primitive-result.json', board.saved)
        self.assertIn('trace-cleanup-result.json', board.saved)


class TraceAndGuardTests(unittest.TestCase):
    def test_trace_requires_complete_pairs_and_supplier_order(self):
        self.assertTrue(worker.audit_trace(trace())['passed'])
        self.assertFalse(worker.audit_trace(trace().replace('16/16', '10/16'))['passed'])
        self.assertFalse(worker.audit_trace(trace().rsplit('\n', 1)[0])['passed'])
        self.assertFalse(worker.audit_trace(trace().replace('err=0', 'err=-5', 1))['passed'])

    def test_original_retained_trace_parser_compatibility(self):
        path = ROOT.parents[2] / 'unused'  # no live access, optional cached original
        path = Path('E:/edk2-samurai-out/charging-management-20261023/pm/pm-trace-private.txt')
        if not path.exists(): self.skipTest('Windows private cache not exposed by this path')
        self.assertTrue(worker.audit_trace(path.read_text())['passed'])

    def test_prior_receipt_requires_approved_terminal_and_actual_pid_state(self):
        c = config(); obj = object.__new__(worker.RealBoard)
        receipt = {'transaction': 'charging-pm-r5', 'terminal': True, 'restored': True, 'worker_exited': True,
                   'boot_id': c['boot_id'], 'worker_pid': 21491,
                   'worker_path': '/root/charging-management-20261023/charging-pm-r5.py'}
        data = json.dumps(receipt).encode(); c['previous_receipt_sha256'] = hashlib.sha256(data).hexdigest()
        for content, expected in [(b'python3\0' + receipt['worker_path'].encode() + b'\0', 'same_worker_alive'),
                                  (b'other-process\0', 'pid_reused'), (b'', 'unknown'),
                                  (FileNotFoundError(), 'absent'), (PermissionError(), 'unknown')]:
            def read(path):
                if path == Path(c['previous_receipt']): return data
                if isinstance(content, Exception): raise content
                return content
            with self.subTest(expected=expected), patch.object(Path, 'read_bytes', read):
                result = obj.previous(c)
            self.assertTrue(result['receipt_valid']); self.assertEqual(result['process_state'], expected)
        receipt['terminal'] = False; bad = json.dumps(receipt).encode()
        c['previous_receipt_sha256'] = hashlib.sha256(bad).hexdigest()
        with patch.object(Path, 'read_bytes', side_effect=[bad, FileNotFoundError()]):
            self.assertFalse(obj.previous(c)['receipt_valid'])

    def test_import_performs_no_mutation_or_process_launch(self):
        source = (ROOT / 'worker.py').read_bytes(); module = types.ModuleType('inert_import')
        with patch.object(Path, 'mkdir') as mkdir, patch.object(Path, 'write_text') as writing, patch.object(subprocess, 'run') as running, patch.object(os, 'umask') as umask:
            exec(compile(source, str(ROOT / 'worker.py'), 'exec'), module.__dict__)
        mkdir.assert_not_called(); writing.assert_not_called(); running.assert_not_called(); umask.assert_not_called()

    def test_primitive_copy_hash_unchanged(self):
        self.assertEqual(hashlib.sha256((ROOT / 'pm-transaction.py').read_bytes()).hexdigest(), worker.PRIMITIVE_SHA256)

    def test_previous_gate_runs_before_any_hardware_or_manager_access(self):
        c = config(); obj = object.__new__(worker.RealBoard)
        obj.live = types.SimpleNamespace(state=unittest.mock.Mock())
        obj.previous = lambda _: {'receipt_valid': True, 'process_state': 'same_worker_alive'}
        evidence = {}; obj.save = lambda name, value: evidence.update({name: value})
        with patch.object(Path, 'read_text', return_value=c['boot_id']), patch.object(worker.os, 'uname', create=True, return_value=types.SimpleNamespace(release=c['release'])), patch.object(Path, 'read_bytes') as reading, patch.object(worker.runpy, 'run_path') as manager:
            with self.assertRaises(worker.PreflightRejected): obj.capture(c, before=True)
        reading.assert_not_called(); manager.assert_not_called(); obj.live.state.assert_not_called()
        self.assertEqual(evidence['previous-transaction-result.json']['process_state'], 'same_worker_alive')

    def test_main_without_execute_never_constructs_live_board(self):
        c = config(); arguments = ['--window-confirmed']
        for key in ['transaction', 'boot_id', 'manifest_sha256', 'release', 'output_root', 'live_helper', 'live_sha256', 'previous_receipt', 'previous_receipt_sha256']:
            arguments += ['--' + key.replace('_', '-'), c[key]]
        with patch.object(worker, 'RealBoard') as factory:
            with self.assertRaises(ValueError): worker.main(arguments)
        factory.assert_not_called()


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromModule(__import__(__name__))
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    report = {'passed': result.wasSuccessful(), 'test_methods': suite.countTestCases(),
              'scope': 'actual candidate dispatch/classification functions and guard checks with fake board; no device/SDK/PM launch',
              'tested_files': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in ['worker.py', 'test-worker.py', 'pm-transaction.py']}}
    (ROOT / 'test-result.json').write_text(json.dumps(report, indent=2) + '\n')
    raise SystemExit(0 if report['passed'] else 1)
