"""Run only six new affected-boundary groups, not the old 11/126 suites."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
OUT = Path('/home/cy122/charging-management-20261023/dwc-device-start-recovery-test-01')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert not OUT.exists(), 'unique output; never replay a running or ended fixture'
OUT.mkdir(parents=True)
command = ['gcc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function',
           '-Wno-unused-parameter', '-g', '-O1', '-fsanitize=address,undefined',
           '-fno-omit-frame-pointer', '-fno-pie', '-no-pie',
           str(HERE/'test-start.c'), '-o', str(OUT/'test-start')]
phases = []
for label, argv in [('compile', command), ('run', [str(OUT/'test-start')])]:
    started = time.monotonic()
    env = dict(os.environ, ASAN_OPTIONS='detect_leaks=1:abort_on_error=1',
               UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
    with (OUT/(label+'.stdout')).open('w') as stdout, (OUT/(label+'.stderr')).open('w') as stderr:
        p = subprocess.Popen(argv, stdout=stdout, stderr=stderr, env=env)
        rc = p.wait()
    phases.append(dict(phase=label, argv=argv, pid=p.pid, terminal=True, returncode=rc,
                       seconds=time.monotonic()-started,
                       stdout_sha256=sha(OUT/(label+'.stdout')),
                       stderr_sha256=sha(OUT/(label+'.stderr'))))
    if rc:
        print((OUT/(label+'.stderr')).read_text())
        break
summary = None
if len(phases)==2 and not phases[-1]['returncode']:
    summary = json.loads((OUT/'run.stdout').read_text().splitlines()[-1])
passed = summary is not None and summary['passed'] and summary['groups']==6 and summary['cases']==20
result = dict(passed=passed, phases=phases, summary=summary,
              files={n:sha(HERE/n) for n in ['test-start.c','test-start.py','gadget.c','core.h',
                         'tested-functions.inc','previous-soft-connect.inc','function-manifest.json','source-result.json']},
              private_output=str(OUT), old_suites_rerun=False, hardware_emulated=False,
              no_new_core_pm_unwind=True, device_access=False)
(HERE/'test-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
raise SystemExit(0 if passed else 1)
