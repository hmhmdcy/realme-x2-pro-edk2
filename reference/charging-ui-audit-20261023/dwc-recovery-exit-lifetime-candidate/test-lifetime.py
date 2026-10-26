"""One new native fixture; no original suite, mount/helper, object or device."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
OUT = Path('/home/cy122/charging-management-20261023/dwc-recovery-exit-lifetime-test-01')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
if sys.flags.optimize:
    raise RuntimeError('Nonoptimized interpreter required')
if OUT.exists():
    raise RuntimeError('Unique output only; never replay a child')
source = json.loads((HERE/'source-result.json').read_bytes())
for name,digest in source['candidate'].items():
    if sha(HERE/name) != digest:
        raise ValueError(name)
OUT.mkdir(parents=True)
argv = ['gcc','-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-function',
        '-Wno-unused-parameter','-g','-O1','-pthread','-fsanitize=address,undefined',
        '-fno-omit-frame-pointer','-fno-pie','-no-pie',str(HERE/'test-lifetime.c'),
        '-o',str(OUT/'test-lifetime')]
phases = []
for label,command in [('compile',argv),('run',[str(OUT/'test-lifetime')])]:
    started = time.monotonic()
    with (OUT/(label+'.stdout')).open('w') as stdout,(OUT/(label+'.stderr')).open('w') as stderr:
        child = subprocess.Popen(command,stdout=stdout,stderr=stderr,env=dict(os.environ,
            ASAN_OPTIONS='detect_leaks=1:abort_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'))
        try:
            print(json.dumps(dict(phase=label,pid=child.pid)),flush=True)
        finally:
            rc = child.wait()
    phases.append(dict(phase=label,argv=command,pid=child.pid,terminal=True,returncode=rc,
        seconds=time.monotonic()-started,stdout_sha256=sha(OUT/(label+'.stdout')),
        stderr_sha256=sha(OUT/(label+'.stderr'))))
    if rc:
        print((OUT/(label+'.stderr')).read_text(),flush=True)
        break
summary = None
if len(phases)==2 and phases[-1]['returncode']==0:
    summary = json.loads((OUT/'run.stdout').read_text().splitlines()[-1])
passed = bool(summary and summary['passed'] and summary['cases']==8)
names = ['prepare.py','gadget.c','core.h','recovery-exit-lifetime.patch','source-result.json',
         'actual-functions.inc','previous-functions.inc','test-lifetime.c','test-lifetime.py']
result = dict(passed=passed,summary=summary,phases=phases,
    files={n:sha(HERE/n) for n in names},private_output=str(OUT),
    boundaries_fake=['IRQ/workqueue primitive','UDC unbind','MMIO/DMA','PM','allocation/free'],
    pthread_mutex_and_condition_join_executed=True,old_7_15_13_24_20_126_and_outcome_suites_rerun=False,
    full_resume_abort_proved=False,device_SSH_USB_storage_helper_SDK_Git_used=False)
(HERE/'test-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(passed=passed,summary=summary,receipt_sha256=sha(HERE/'test-result.json'))),flush=True)
raise SystemExit(0 if passed else 1)
