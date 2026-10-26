"""Run only the new caller/resource counterexample, not root's eight groups."""
from pathlib import Path
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
flags = ['-std=c11', '-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter',
         '-fsanitize=address,undefined', '-fno-omit-frame-pointer']
p = subprocess.run(['gcc', *flags, str(HERE / 'test-unwind.c'), '-o', str(HERE / 'test-unwind')],
                   text=True, capture_output=True, timeout=30)
assert p.returncode == 0, p.stderr
r = subprocess.run([str(HERE / 'test-unwind')], text=True, capture_output=True, timeout=15)
assert r.returncode == 0, r.stderr
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
result = {'status': 'changes-required', 'new_counterexamples': 2, 'control': 1,
          'compile_stderr': p.stderr, 'stdout': r.stdout, 'runtime_stderr': r.stderr,
          'flags': flags, 'actual_function_fixture': 'actual-functions.inc',
          'files': {n: sha(HERE / n) for n in ['actual-functions.inc', 'test-unwind.c',
                    'prepare-repro.py', 'run-repro.py', 'source-manifest.json', 'extraction-result.json']},
          'root_8_or_other_old_suites_rerun': False, 'root_candidate_modified': False,
          'complete_runtime_pm_simulated': False,
          'hardware_resource_boundary': 'fake clocks/reset/core-PHY init and MMIO; actual caller/control/exit bodies',
          'phone_ssh_usb_sdk_accessed': False, 'shared_sources_modified': False}
(HERE / 'repro-result.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())
print(json.dumps(result, indent=2))
