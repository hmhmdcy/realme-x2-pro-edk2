"""One revision2 actual classify counterexample; do not rerun prior suites."""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sha = lambda raw: hashlib.sha256(raw).hexdigest()
spec = importlib.util.spec_from_file_location('existing_pm_fixture_helpers', HERE / 'test-new-boundaries.py')
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)  # inert helpers only; its main/10 methods are not run
worker = fixture.worker


class ReturnedFactTest(unittest.TestCase):
    def test_original_primitive_cleanup_failure_keeps_returned_fact(self):
        with tempfile.TemporaryDirectory() as temporary:
            c, *_ = fixture.request_fixture(Path(temporary))
            board = fixture.FakeBoard(c)
            primitive = {**board.primitive, 'outcome': 'failed', 'mem_returned': True,
                         'cleanup': 'unknown_or_failed', 'cleanup_error': {'errno': 5, 'type': 'OSError'}}
            result = worker.classify(c, board.before, primitive, board.after, fixture.trace_text(), {'passed': True}, {})
            self.assertTrue(result['functional_facts']['returned'])
            self.assertTrue(result['trace_evidence']['returned'])
            self.assertEqual(result['functional_facts']['estimated_residency_seconds'], 15)
            self.assertFalse(result['functional_checks']['primitive_returned'])
            self.assertFalse(result['functional_checks']['own_alarm_cleanup_safe'])
            self.assertFalse(result['local_functional_checks_passed'])
            self.assertFalse(result['whole_system_accepted'])
            # Negative fact control: failing before mem return must stay false.
            primitive['mem_returned'] = False
            result = worker.classify(c, board.before, primitive, board.after, fixture.trace_text(), {'passed': True}, {})
            self.assertFalse(result['functional_facts']['returned'])
            # Original returned outcome still satisfies the stricter operation gate.
            result = worker.classify(c, board.before, board.primitive, board.after, fixture.trace_text(), {'passed': True}, {})
            self.assertTrue(result['functional_checks']['primitive_returned'])
            self.assertTrue(result['functional_facts']['returned'])


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ReturnedFactTest))
    old = (HERE / 'history/revision-1/worker.py').read_text()
    new = (HERE / 'worker.py').read_text()
    old_expression = "functional = {'returned': checks['primitive_returned'],"
    new_expression = "functional = {'returned': primitive.get('mem_returned') is True,"
    assert new.count(new_expression) == old.count(old_expression) == 1
    assert new.replace(new_expression, old_expression) == old
    receipt = {'passed': result.wasSuccessful(), 'new_test_methods': result.testsRun,
               'cases': ['actual primitive RTC-cleanup-failed terminal preserves mem return and duration',
                         'mem not returned remains false', 'returned outcome retains strict operation gate'],
               'tested_files': {name: sha((HERE / name).read_bytes()) for name in ['worker.py', 'test-returned-fact.py', 'test-new-boundaries.py']},
               'only_worker_delta': {'old_expression': old_expression, 'new_expression': new_expression},
               'prior10_27_29_126_rerun': False, 'device_trace_PM_build_SDK_Git': False}
    (HERE / 'returned-fact-test-result.json').write_text(json.dumps(receipt, indent=2) + '\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
