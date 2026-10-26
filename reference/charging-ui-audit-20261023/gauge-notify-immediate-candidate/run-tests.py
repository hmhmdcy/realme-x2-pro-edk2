"""Only the new actual callback/gate cases; no original current or charging suite."""
from pathlib import Path
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
PRIVATE = Path('/home/cy122/charging-management-20261023/gauge-notify-immediate-tests-02')
assert not PRIVATE.exists()
PRIVATE.mkdir(parents=True)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
source = json.loads((HERE / 'source-result.json').read_bytes())
assert sha(HERE / 'bq27xxx_battery.c') == source['candidate_source_sha256']
assert sha(HERE / 'actual-functions.inc') == source['actual_functions_sha256']
flags = ['-std=c11', '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-no-pie']
command = ['gcc', *flags, str(HERE / 'test-callback.c'), '-o', str(PRIVATE / 'test-callback')]
compile_result = subprocess.run(command, capture_output=True, text=True)
(PRIVATE / 'compile.txt').write_text(compile_result.stdout + compile_result.stderr)
assert compile_result.returncode == 0, compile_result.stderr
run = subprocess.run([str(PRIVATE / 'test-callback')], capture_output=True, text=True)
(PRIVATE / 'stdout.txt').write_text(run.stdout); (PRIVATE / 'stderr.txt').write_text(run.stderr)
groups = [x[4:] for x in run.stdout.splitlines() if x.startswith('ok: ')]
assert run.returncode == 0 and not run.stderr and len(groups) == 7
result = {'passed': True, 'group_count': 7, 'groups': groups, 'returncode': run.returncode,
          'actual_functions': ['bq27xxx_samurai_instant', 'bq27xxx_external_power_changed'],
          'compile_command': command, 'compile_diagnostic_bytes': len(compile_result.stderr),
          'ASan_UBSan_Werror': True,
          'files': {n: sha(HERE / n) for n in ['bq27xxx_battery.c', 'notify-immediate.patch', 'actual-functions.inc',
                                            'test-callback.c', 'prepare.py', 'run-tests.py', 'source-result.json']},
          'private_output': str(PRIVATE), 'stdout_sha256': sha(PRIVATE / 'stdout.txt'),
          'workqueue_boundary': 'fake records actual callback requests for same pending/running work; not Linux scheduler concurrency proof',
          'old_suites_rerun': False, 'device_SDK_Image_Git_used': False}
(HERE / 'test-result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'passed': True, 'groups': 7, 'receipt_sha256': sha(HERE / 'test-result.json')}))
