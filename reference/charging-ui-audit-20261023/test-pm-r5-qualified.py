from pathlib import Path
import importlib.util
import unittest

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('qualified', ROOT / 'audit-pm-r5-qualified.py')
audit = importlib.util.module_from_spec(spec); spec.loader.exec_module(audit)


class EvidenceTests(unittest.TestCase):
    def test_ring_roll_with_complete_baseline_tail_is_accepted(self):
        result = audit.ordered_log_tail('a\nb\nc\n', 'b\nc\nd\n')
        self.assertTrue(result['complete_since_baseline'])
        self.assertEqual(result['old_head_lines_dropped'], 1)
        self.assertEqual(result['new_lines'], ['d'])

    def test_missing_baseline_tail_is_not_complete(self):
        self.assertFalse(audit.ordered_log_tail('a\nb\nc\n', 'd\ne\n')['complete_since_baseline'])

    def test_identical_logs_have_no_new_lines(self):
        result = audit.ordered_log_tail('a\nb\n', 'a\nb\n')
        self.assertTrue(result['complete_since_baseline']); self.assertEqual(result['new_lines'], [])

    def test_rtc_counter_one_never_overrides_long_residency(self):
        runtime = {'sysfs_result': {'errno': 0}, 'residency_seconds': 3396.192, 'rtc_irq_delta': 1}
        self.assertFalse(audit.planned_rtc_window(runtime, True))

    def test_timing_alone_without_rtc_attribution_is_insufficient(self):
        runtime = {'sysfs_result': {'errno': 0}, 'residency_seconds': 15, 'rtc_irq_delta': 1}
        self.assertFalse(audit.planned_rtc_window(runtime, False))
        self.assertTrue(audit.planned_rtc_window(runtime, True))


if __name__ == '__main__':
    unittest.main()
