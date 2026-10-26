"""Only the optional software-window candidate, with actual function bodies."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

HERE = Path(__file__).resolve().parent
subprocess.run([sys.executable, '-B', str(HERE / 'prepare-candidate-fixture.py')], check=True)
flags = ['-std=gnu11', '-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter',
         '-Wno-unused-function', '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-pthread']
compile = subprocess.run(['gcc', *flags, str(HERE / 'test-candidate.c'),
                          '-o', str(HERE / 'test-candidate')], capture_output=True)
run = subprocess.run([str(HERE / 'test-candidate')], capture_output=True, timeout=15) if not compile.returncode else None
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
result = {'passed': compile.returncode == 0 and run is not None and run.returncode == 0,
          'boundary_groups': 9, 'compile_returncode': compile.returncode,
          'compile_stderr': compile.stderr.decode(), 'runtime_returncode': run.returncode if run else None,
          'runtime_stdout': run.stdout.decode() if run else '', 'runtime_stderr': run.stderr.decode() if run else '',
          'flags': flags, 'tested_files': {name: sha(HERE / name) for name in [
              'eud.c', 'eud-com-window.h', 'candidate-functions.inc', 'candidate-function-manifest.json',
              'fake-eud-os.h', 'test-candidate.c', 'prepare-candidate.py', 'prepare-candidate-fixture.py',
              'run-candidate-tests.py', 'window-implementation.inc']},
          'phone_accessed': False, 'ssh_executed': False, 'usb_accessed': False, 'sdk_invoked': False,
          'shared_source_modified': False, 'consumer_present': False, 'csr_or_ahb_window_writes': False,
          'scope': 'actual software window with fake OS/MMIO and one pthread lifetime race; no electrical or USB acceptance'}
(HERE / 'candidate-test-result.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())
print(json.dumps(result, indent=2))
raise SystemExit(0 if result['passed'] else 1)
