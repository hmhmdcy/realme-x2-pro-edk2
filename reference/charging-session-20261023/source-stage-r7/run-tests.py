"""Run only the focused disk-stage tests and bind the actual worker bytes."""
from pathlib import Path
import datetime
import hashlib
import importlib.util
import io
import json
import platform
import time
import unittest

here = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('r7_stage_tests', here / 'test-stage.py')
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
suite = unittest.defaultTestLoader.loadTestsFromModule(module)
cases = [test.id() for group in suite for test in group]
output = io.StringIO(); start = time.monotonic()
result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
receipt = dict(passed=result.wasSuccessful(), worker_sha256=digest(here / 'stage-r7.py'),
               tests_run=result.testsRun, cases=cases, output=output.getvalue(),
               timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
               python=platform.python_version(), elapsed_seconds=time.monotonic() - start,
               files={name: digest(here / name) for name in ['stage-r7.py', 'test-stage.py', 'run-tests.py']},
               scope='focused actual stage transaction and real temp-file atomic write/fsync/rename failures; fake device/manager boundaries',
               payload_sha256=module.m.PAYLOAD, old_manifest_sha256=module.m.OLD, new_manifest_sha256=module.m.NEW,
               phone_accessed=False, ssh_executed=False, sdk_accessed=False, reboot_executed=False,
               prior_67_51_62_suites_repeated=False)
(here / 'test-result.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({key: receipt[key] for key in ['passed', 'worker_sha256', 'tests_run', 'files']}, indent=2))
raise SystemExit(0 if result.wasSuccessful() else 1)
