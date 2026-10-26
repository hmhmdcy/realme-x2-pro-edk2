from pathlib import Path
import hashlib,importlib.util,io,json,sys,unittest
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('icon_r8_affected',HERE/'test-migration.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(module))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
receipt=dict(schema='charging-icon-r8-eud-off-migration-tests-v1',passed=result.wasSuccessful(),tests_run=result.testsRun,
 launcher_sha256=sha(HERE/'launcher.py'),identity_pins_sha256=sha(HERE/'identity-pins.json'),
 sha256=module.launcher.FROZEN,manifest_sha256=module.launcher.MANIFEST,
 tested_files={n:sha(HERE/n) for n in ['launcher.py','capture-entry.py','test-migration.py','run-migration-tests.py']},
 historical_evidence=dict(collector_tests=32,old_launcher_migration_tests=8,rerun=False),
 phone_accessed=False,ssh_executed=False,SDK_invoked=False,Git_invoked=False,output=stream.getvalue())
(HERE/'migration-test-result.json').write_text(json.dumps(receipt,indent=2)+'\n');print(stream.getvalue());print(json.dumps(dict(passed=receipt['passed'],tests_run=result.testsRun)))
raise SystemExit(0 if result.wasSuccessful() else 1)
