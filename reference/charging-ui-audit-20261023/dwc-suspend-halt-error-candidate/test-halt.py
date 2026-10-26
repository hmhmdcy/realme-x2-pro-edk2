"""Only newly affected actual gadget/core combinations, no old suite replay."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
OUT=Path('/home/cy122/charging-management-20261023/dwc-suspend-halt-test-01')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if sys.flags.optimize:raise RuntimeError('nonoptimized interpreter required')
assert not OUT.exists(),'one new output; never retry an old process'
OUT.mkdir(parents=True)
compile_argv=['gcc','-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-unused-parameter',
 '-g','-O1','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie',
 str(HERE/'test-halt.c'),'-o',str(OUT/'test-halt')]
phases=[]
for label,argv in [('compile',compile_argv),('run',[str(OUT/'test-halt')])]:
 started=time.monotonic()
 with (OUT/(label+'.stdout')).open('w') as stdout,(OUT/(label+'.stderr')).open('w') as stderr:
  child=subprocess.Popen(argv,stdout=stdout,stderr=stderr,env=dict(os.environ,
        ASAN_OPTIONS='detect_leaks=1:abort_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'))
  try:print(json.dumps(dict(phase=label,pid=child.pid)),flush=True)
  finally:rc=child.wait()
 phases.append(dict(phase=label,argv=argv,pid=child.pid,terminal=True,returncode=rc,
  seconds=time.monotonic()-started,stdout_sha256=sha(OUT/(label+'.stdout')),stderr_sha256=sha(OUT/(label+'.stderr'))))
 if rc:
  print((OUT/(label+'.stderr')).read_text(),flush=True);break
summary=None
if len(phases)==2 and phases[-1]['returncode']==0:
 summary=json.loads((OUT/'run.stdout').read_text().splitlines()[-1])
passed=bool(summary and summary['passed'] and summary['cases']==13)
files=['prepare.py','gadget.c','suspend-halt-error.patch','source-result.json','test-halt.c','test-halt.py',
       'tested-functions.inc','previous-functions.inc']
result=dict(passed=passed,summary=summary,phases=phases,files={n:sha(HERE/n) for n in files},
 private_output=str(OUT),old_24_20_126_suites_rerun=False,
 MMIO_DMA_request_IRQ_PM_and_reconnect_boundaries_fake=True,
 full_resume_unwind_complete=False,device_storage_helper_SDK_Git_used=False)
(HERE/'test-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(passed=passed,summary=summary,receipt_sha256=sha(HERE/'test-result.json'))),flush=True)
raise SystemExit(0 if passed else 1)
