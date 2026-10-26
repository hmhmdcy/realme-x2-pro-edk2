"""New affected actual functions only; no old 20/126 tests or storage helper."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import time

HERE = Path(__file__).resolve().parent
OUT = Path('/home/cy122/charging-management-20261023/dwc-pm-susphy-tests-02')
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
OUT.mkdir(parents=True, exist_ok=False)
commands = [('compile', ['gcc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function',
             '-Wno-unused-parameter', '-g', '-O1', '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
             '-fno-pie', '-no-pie', str(HERE / 'test-susphy.c'), '-o', str(OUT / 'test-susphy')]),
            ('run', [str(OUT / 'test-susphy')])]
phases = []
for label, argv in commands:
    started = time.monotonic()
    with (OUT / (label + '.stdout')).open('xb') as stdout, (OUT / (label + '.stderr')).open('xb') as stderr:
        child = subprocess.Popen(argv, stdout=stdout, stderr=stderr,
                 env=dict(os.environ, ASAN_OPTIONS='detect_leaks=1:abort_on_error=1', UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'))
        rc = child.wait()
    phases.append({'phase': label, 'argv': argv, 'pid': child.pid, 'terminal': True, 'returncode': rc,
                   'seconds': time.monotonic() - started, 'stdout_sha256': sha(OUT / (label + '.stdout')),
                   'stderr_sha256': sha(OUT / (label + '.stderr'))})
    if rc:
        print((OUT / (label + '.stderr')).read_text())
        break
summary = json.loads((OUT / 'run.stdout').read_text()) if len(phases) == 2 and phases[-1]['returncode'] == 0 else None
passed = summary is not None and summary['passed'] and summary['cases'] == 24
result = {'passed': passed, 'summary': summary, 'phases': phases,
          'files': {name: sha(HERE / name) for name in ['prepare.py', 'core.c', 'suspend-susphy.patch', 'source-result.json',
                    'test-susphy.py', 'test-susphy.c', 'tested-functions.inc', 'original-suspend.inc']},
          'private_output': str(OUT), 'old_20_126_rerun': False,
          'kernel_object_or_Image_built': False, 'storage_helper_or_device_or_SDK_or_Git_used': False,
          'MMIO_PM_IRQ_callbacks_are_fake_boundaries': True, 'full_resume_error_unwind_complete': False}
(HERE / 'test-result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'passed': passed, 'summary': summary, 'receipt_sha256': sha(HERE / 'test-result.json')}))
raise SystemExit(0 if passed else 1)
