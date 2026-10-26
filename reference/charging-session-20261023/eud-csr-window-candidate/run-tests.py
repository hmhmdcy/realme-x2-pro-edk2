"""Only the new CSR-stage actual-function boundaries; no old suites rerun."""
from pathlib import Path
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
flags = ['-std=gnu11', '-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter',
         '-Wno-unused-function', '-fsanitize=address,undefined',
         '-fno-omit-frame-pointer', '-pthread']
compile = subprocess.run(['gcc', *flags, str(HERE / 'test-csr.c'), '-o', str(HERE / 'test-csr')],
                         capture_output=True, text=True, timeout=30)
assert compile.returncode == 0, compile.stderr
run = subprocess.run([str(HERE / 'test-csr')], capture_output=True, text=True, timeout=20)
assert run.returncode == 0, run.stderr
groups = [s[4:] for s in run.stdout.splitlines() if s.startswith('ok: ')]
assert len(groups) == 9, run.stdout
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
names = ['eud.c', 'eud-com-window.h', 'candidate-functions.inc', 'fake-eud-os.h',
         'test-csr.c', 'csr-implementation.inc', 'prepare-candidate.py', 'run-tests.py']
result = {'passed': True, 'groups': groups, 'compiler_flags': flags,
          'compile_stderr': compile.stderr, 'runtime_stdout': run.stdout,
          'runtime_stderr': run.stderr, 'tested_files': {n: sha(HERE / n) for n in names},
          'old_r2_or_r1_suites_rerun': False,
          'scope': 'actual CSR/quiet/PM/remove functions with fake OS/MMIO and controlled pthread serialization',
          'hardware_route_usb_apsd_or_budget_proven': False,
          'phone_ssh_sdk_accessed': False, 'shared_sources_modified': False}
(HERE / 'test-result.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())
print(json.dumps(result, indent=2))
