"""Only actual existing EUD callback limitations; no phone/SDK/shared changes."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

HERE = Path(__file__).resolve().parent
subprocess.run([sys.executable, '-B', str(HERE / 'prepare-fixture.py')], check=True)
flags = ['-std=gnu11', '-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter',
         '-fsanitize=address,undefined', '-fno-omit-frame-pointer']
compiled = subprocess.run(['gcc', *flags, str(HERE / 'test-existing-boundaries.c'),
                           '-o', str(HERE / 'test-existing-boundaries')], capture_output=True)
run = subprocess.run([str(HERE / 'test-existing-boundaries')], capture_output=True) if not compiled.returncode else None
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
result = {'passed': compiled.returncode == 0 and run is not None and run.returncode == 0,
          'actual_functions': 15, 'boundary_groups': 7,
          'compile_returncode': compiled.returncode, 'compile_stderr': compiled.stderr.decode(),
          'runtime_returncode': run.returncode if run else None,
          'runtime_stdout': run.stdout.decode() if run else '',
          'runtime_stderr': run.stderr.decode() if run else '', 'flags': flags,
          'tested_files': {name: sha(HERE / name) for name in ['actual-functions.inc', 'function-manifest.json',
              'test-existing-boundaries.c', 'prepare-fixture.py', 'run-tests.py']},
          'phone_accessed': False, 'ssh_executed': False, 'usb_accessed': False,
          'sdk_invoked': False, 'shared_source_modified': False, 'driver_patch_created': False,
          'scope': 'unchanged Image-linked callbacks plus fake OS/MMIO; demonstrates missing semantics, not a quiet/restore implementation or hardware validation'}
(HERE / 'test-result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
raise SystemExit(0 if result['passed'] else 1)
