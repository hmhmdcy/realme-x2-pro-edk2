"""New completed IRQ+PM module binding only; old packaging suites are reused."""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import os
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('actual_irq_pm_package', HERE / 'cohort.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
PROOF = json.loads((HERE / 'module-input.json').read_bytes())
PINS = json.loads((HERE / 'input-pins.json').read_bytes())


def actual():
    documents = [json.loads(c.pinned(PROOF[name]).read_bytes())
                 for name in ['delivery', 'receipt', 'execution', 'identity', 'source_delivery']]
    parsed = c.module_identity(c.pinned(PROOF['module']).read_bytes(), c.USB)
    image = json.loads(c.pinned(PINS['receipts']['Image504_build']).read_bytes())['build']
    return documents + [parsed, image]


class ActualModuleBinding(unittest.TestCase):
    def test_actual47_module_and_original_waits(self):
        args = actual()
        c.validate_module_completion(*args)
        self.assertEqual(args[1]['strong_import_count'], 47)
        self.assertEqual(args[2]['tool_session_id'], 30261)
        self.assertEqual([p['pid'] for p in args[2]['commands']], [832, 2647])
        self.assertEqual(args[5]['sha256'], 'd04608ad80a90288c32705bbfcfd3855738d7b09f207ae2aa4268f7c0a167037')

    def test_unknown_completion_and_wrong_lineage_rejected(self):
        cases = [
            (0, lambda x: x.update(passed=False)),
            (1, lambda x: x['commands'][1].update(terminal=False)),
            (2, lambda x: x.update(outer_exec_exit_code=255)),
            (1, lambda x: x.update(strong_import_count=43)),
            (1, lambda x: x.update(generated_autoconf_exact_Image502=False)),
            (1, lambda x: x.update(diagnostics=['warning'])),
            (5, lambda x: x.update(resident_note_sha256='4930d9499784484fc2faf89ecfd579d1f81c705240544c56193f59cc6d2698ff')),
            (6, lambda x: x['outputs']['vmlinux.symvers'].update(sha256='0' * 64)),
        ]
        original = actual()
        for index, mutate in cases:
            args = copy.deepcopy(original)
            mutate(args[index])
            with self.subTest(component=index), self.assertRaises(ValueError):
                c.validate_module_completion(*args)

    def test_old2691_proof_cannot_be_relabelled(self):
        wrong = copy.deepcopy(PROOF)
        wrong['receipt']['sha256'] = 'f56dd0ed9f082ef2509c5a2daa62fa4f7542dc8af99d6ffe62f483e87d305e95'
        with self.assertRaisesRegex(ValueError, 'actual completed module input: receipt'):
            c.complete_inputs(wrong)
        self.assertFalse(c.local(c.OUT).exists())


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ActualModuleBinding))
    names = ['cohort.py', 'source-pins.json', 'input-pins.json', 'module-input.json', 'test-module-binding.py']
    report = {'passed': result.wasSuccessful(), 'methods': result.testsRun, 'negative_completion_or_lineage_cases': 9,
              'pid': os.getpid(), 'old_five_or_historical_matrix_rerun': False,
              'tested_files': {n: hashlib.sha256((HERE / n).read_bytes()).hexdigest() for n in names},
              'module_actual_receipt_sha256': PROOF['receipt']['sha256'], 'device_accessed': False}
    (HERE / 'module-binding-test-result.json').write_text(json.dumps(report, indent=2) + '\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
