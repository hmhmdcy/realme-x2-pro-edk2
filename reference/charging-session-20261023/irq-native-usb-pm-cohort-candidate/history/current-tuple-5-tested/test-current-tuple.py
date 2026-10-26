"""Only the current raw-manifest/IRQ tuple and missing-material boundaries."""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import os
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('current_irq_pm_package', HERE / 'cohort.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
PINS = json.loads((HERE / 'input-pins.json').read_bytes())
RAW = c.pinned(PINS['base_manifest']).read_bytes()
DIGEST = hashlib.sha256(b'test-only new module bytes; never materialized').hexdigest()


class CurrentTuple(unittest.TestCase):
    def test_three_byte_spans_only(self):
        result = c.make_manifest(RAW, DIGEST)
        self.assertEqual(result, RAW.replace(c.OLD_USB.encode(), DIGEST.encode()).replace(
            json.dumps(c.OLD_REVISION).encode(), json.dumps(c.REVISION).encode()))
        self.assertEqual(result.count(DIGEST.encode()), 2)
        self.assertEqual(json.loads(result)['modules']['samurai-mp2650']['sha256'], c.CHARGER)
        self.assertEqual(json.loads(result)['modules']['samurai-gauge-protection']['sha256'], c.PROTECTION)
        c.check_manifest_delta(RAW, result, DIGEST)

    def test_manifest_mismatch_and_extra_change_rejected(self):
        for raw, digest in [(RAW + b' ', DIGEST), (RAW, c.OLD_USB), (RAW, 'not-a-hash')]:
            with self.subTest(raw_changed=raw != RAW, digest=digest):
                with self.assertRaises(ValueError):
                    c.make_manifest(raw, digest)
        new = c.make_manifest(RAW, DIGEST)
        with self.assertRaises(ValueError):
            c.check_manifest_delta(RAW, new.replace(b'900000', b'950000'), DIGEST)

    def test_only_current_irq_carrier_and_modules(self):
        old = json.loads(RAW)
        c.validate_current_tuple(old, PINS['carriers'])
        for field, wrong in [('samurai-mp2650', '10ec06fb9d798d72e08495617cfc04e7e49c77e536a12f205053e9cdbfa6297f'),
                             ('samurai-gauge-protection', '75b97e0d6b906ec600171ce68adec6f25a91556758f76bbf3d563cf831e783c7'),
                             (c.USB, '2691c3ceb6245c7c4999c122f015ad93588dce5928b8cd982a5ac725539c4448')]:
            bad = copy.deepcopy(old)
            bad['modules'][field]['sha256'] = wrong
            with self.subTest(field=field), self.assertRaises(ValueError):
                c.validate_current_tuple(bad, PINS['carriers'])
        for key, wrong in [('boot', '97811cc4ae13b36fec98b2eae7cd54a4f12bca988864df0f3d8f663a8c67f695'),
                           ('native_DTB', '9271d9cc33b3701ad0675c6345d43e9a5c404aa6c192126edc3eb715b0914358'),
                           ('rollback_logdump', c.FORWARD_FAT)]:
            bad = copy.deepcopy(PINS['carriers'])
            bad[key]['sha256'] = wrong
            with self.subTest(carrier=key), self.assertRaises(ValueError):
                c.validate_current_tuple(old, bad)

    def test_current_full_carrier_receipt_reused(self):
        carrier = PINS['carrier']
        receipt = json.loads(c.pinned(carrier['receipt']).read_bytes())
        c.validate_carrier(receipt, carrier, {'sha256': c.IMAGE, 'bytes': 59243008})
        self.assertEqual(carrier['logdump']['sha256'], c.FORWARD_FAT)

    def test_missing_actual_new_module_before_output(self):
        original = c.HERE
        with tempfile.TemporaryDirectory() as temporary:
            c.HERE = Path(temporary)
            try:
                with self.assertRaisesRegex(ValueError, r'actual IRQ\+PM module input not yet supplied'):
                    c.local_inputs()
                self.assertEqual(list(Path(temporary).iterdir()), [])
            finally:
                c.HERE = original


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(CurrentTuple)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    files = ['cohort.py', 'source-pins.json', 'input-pins.json', 'test-current-tuple.py']
    report = {'passed': result.wasSuccessful(), 'methods': result.testsRun, 'pid': os.getpid(),
              'scope': 'new raw manifest/current tuple/missing module only; inherited packaging suites not rerun',
              'tested_files': {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest() for name in files},
              'actual_new_module_materialized': False, 'device_accessed': False}
    (HERE / 'current-tuple-test-result.json').write_text(json.dumps(report, indent=2) + '\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
