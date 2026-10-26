"""Compile real candidate bodies/headers with boundary fakes, never deploy."""
from pathlib import Path
import difflib
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
OUT = Path('/home/cy122/charging-session-20261023/kernel-v2')
OUT.mkdir(parents=True, exist_ok=True)
source = (HERE / 'samurai-mp2650.c').read_text()
functions = {}
for function, target in [('sm_step_locked', 'sm-step-extracted.inc'),
                         ('sm_gauge_sample', 'gauge-extracted.inc')]:
    start = source.index('static int ' + function + '(')
    end = source.index('\n}\n', start) + 3
    body = source[start:end]
    (HERE / target).write_text(body)
    functions[function] = hashlib.sha256(body.encode()).hexdigest()
result = {}
for test in ['test-hold', 'test-gauge', 'test-step', 'test-oem-full', 'test-oem-differential', 'test-core']:
    command = ['gcc', '-std=c11', '-g', '-Wall', '-Wextra', '-Werror',
               '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
               '-I' + str(HERE), str(HERE / (test + '.c')), '-o', str(OUT / test)]
    subprocess.run(command, check=True)
    run = subprocess.run([str(OUT / test)], capture_output=True, text=True)
    print(test + ': ' + run.stdout, end='')
    print(run.stderr, end='')
    run.check_returncode()
    result[test] = {'result': json.loads(run.stdout), 'command': command,
                    'sha256': hashlib.sha256((HERE / (test + '.c')).read_bytes()).hexdigest()}
names = ['samurai-mp2650.c', 'mp2650-core.h', 'oem-full-cycle.h',
         'charging-notify.h', 'oem-profile.h', 'charge-cycle.h',
         'gauge-i2c.h', 'gauge-protocol.h']
baseline = json.loads((HERE / 'baseline.json').read_text())
frozen_v1 = HERE.parent / 'full-integration-candidate'
unchanged = {name: hashlib.sha256((frozen_v1 / name).read_bytes()).hexdigest() == digest
             for name, digest in baseline.items()}
assert all(unchanged.values()), 'frozen v1 changed while candidate testing'
production = HERE.parent.parent / 'charging-management-20261023'
main_baseline = json.loads((frozen_v1 / 'baseline.json').read_text())
main_unchanged = {name: hashlib.sha256((production / name).read_bytes()).hexdigest() == digest
                  for name, digest in main_baseline.items()}
assert all(main_unchanged.values()), 'main changed while candidate testing'
patch = ''
for name in names:
    original = HERE / 'baseline' / name
    before = original.read_text() if original.exists() else ''
    after = (HERE / name).read_text()
    if before != after:
        patch += ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                         fromfile='a/' + name if original.exists() else '/dev/null', tofile='b/' + name))
(HERE / 'full-integration.patch').write_text(patch)
report = {'passed': True, 'tests': result, 'extracted_functions': functions,
          'candidate_files': {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest() for name in names},
          'frozen_v1_unchanged': unchanged, 'main_unchanged': main_unchanged, 'baseline': baseline,
          'patch_sha256': hashlib.sha256(patch.encode()).hexdigest(),
          'scope': 'Exact candidate step/gauge bodies plus real headers and masked transactions, host sanitizers only',
          'kernel_module_built': False, 'phone_accessed': False, 'sdk_accessed': False,
          'shared_kernel_storage_modified': False}
(HERE / 'test-result.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'passed': True, 'tests': {k: v['result'] for k, v in result.items()},
                  'candidate_files': report['candidate_files']}, indent=2))
