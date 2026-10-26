"""Run only R7 affected paths; no device or old 32/13 test repetition."""
from pathlib import Path
import datetime
import hashlib
import importlib.util
import io
import json
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('r7_tests',HERE/'test-migration.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
stream=io.StringIO()
result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(module))
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
receipt=dict(schema='charging-icon-r7-migration-tests-v1',passed=result.wasSuccessful(),tests_run=result.testsRun,
    launcher_sha256=sha(HERE/'launcher.py'),identity_pins_sha256=sha(HERE/'identity-pins.json'),
    sha256=module.launcher.FROZEN,manifest_sha256=module.launcher.MANIFEST,
    historical_evidence={'collector_tests':32,'launcher_tests':13,'rerun':False,
        'scope':'generic worker/audit history only; no R7 physical result claimed'},
    phone_accessed=False,ssh_executed=False,sdk_accessed=False,
    timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),output=stream.getvalue())
(HERE/'migration-test-result.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(stream.getvalue());print(json.dumps({k:receipt[k] for k in ['passed','tests_run','launcher_sha256','identity_pins_sha256']}))
raise SystemExit(0 if result.wasSuccessful() else 1)
