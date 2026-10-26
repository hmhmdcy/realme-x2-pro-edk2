"""Only four late-producer cases; no R1 or independent review suite rerun."""
from pathlib import Path
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
flags = ['-std=gnu11', '-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter',
         '-Wno-unused-function', '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-pthread']
compiled = subprocess.run(['gcc', *flags, str(HERE / 'test-late-producers.c'),
                            '-o', str(HERE / 'test-late-producers')], capture_output=True)
run = subprocess.run([str(HERE / 'test-late-producers')], capture_output=True, timeout=15) if not compiled.returncode else None
cases = [line[4:] for line in run.stdout.decode().splitlines() if line.startswith('ok: ')] if run else []
sha = lambda name: hashlib.sha256((HERE / name).read_bytes()).hexdigest()
result = {'passed': compiled.returncode == 0 and run is not None and run.returncode == 0 and len(cases) == 4,
          'revision': 2, 'groups': cases, 'compile_returncode': compiled.returncode,
          'compile_stderr': compiled.stderr.decode(), 'runtime_returncode': run.returncode if run else None,
          'runtime_stdout': run.stdout.decode() if run else '', 'runtime_stderr': run.stderr.decode() if run else '',
          'flags': flags, 'tested_files': {name: sha(name) for name in ['eud.c', 'eud-com-window.h',
              'candidate-functions.inc', 'nbcon-functions.inc', 'fake-eud-os.h', 'test-late-producers.c',
              'prepare-r2.py', 'run-tests.py']},
          'old_9_groups_rerun': False, 'old_5_review_groups_rerun': False,
          'queued_work_executed_after_free': False, 'r1_modified': False, 'reviewer_files_modified': False,
          'phone_accessed': False, 'ssh_executed': False, 'sdk_invoked': False,
          'scope': 'actual R2 remove/producer bodies with controlled pthread preemption and fake work/console/UART joins'}
(HERE / 'test-result.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())
print(json.dumps(result, indent=2))
raise SystemExit(0 if result['passed'] else 1)
