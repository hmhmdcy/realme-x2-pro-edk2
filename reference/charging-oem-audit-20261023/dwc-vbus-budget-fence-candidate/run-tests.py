"""Actual software-budget functions, fake I/O and real blocked-thread join only."""
from pathlib import Path
import hashlib,json,subprocess,time
HERE=Path(__file__).resolve().parent
OUT=Path('/home/cy122/charging-management-20261023/dwc-vbus-budget-fence-tests-02')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=json.loads((HERE/'source-result.json').read_bytes());assert source['passed']
for name,pin in source['candidate'].items():assert sha(HERE/name)==pin
for name,pin in source['extracts'].items():assert sha(HERE/name)==pin
assert not OUT.exists();OUT.mkdir(mode=0o700)
commands=[]
for label,argv in [('compile',['gcc','-std=c11','-O1','-g','-Wall','-Wextra','-Werror','-pthread',
        '-Wno-unused-parameter','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(HERE/'test-budget.c'),'-o',str(OUT/'test-budget')]),
        ('test',[str(OUT/'test-budget')])]:
    started=time.monotonic();child=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    stdout,stderr=child.communicate();rc=child.wait()
    (OUT/(label+'-stdout-private.txt')).write_bytes(stdout);(OUT/(label+'-stderr-private.txt')).write_bytes(stderr)
    commands.append(dict(label=label,argv=argv,pid=child.pid,terminal=True,returncode=rc,seconds=time.monotonic()-started,
        stdout_sha256=hashlib.sha256(stdout).hexdigest(),stderr_sha256=hashlib.sha256(stderr).hexdigest()))
    if rc or stderr:
        (HERE/'test-attempt-02-result.json').write_text(json.dumps(dict(passed=False,commands=commands),indent=2)+'\n')
        raise RuntimeError((rc,stderr.decode(errors='replace')))
actual=json.loads(stdout);assert actual['passed'] and actual['actual_function_cases']==20
names=['core.c','core.h','gadget.c','budget-work.c.inc','actual-budget-core.inc','actual-budget-gadget.inc',
       'actual-old-worker.inc','actual-old-pm.inc','actual-provider.inc','test-budget.c','run-tests.py']
result=dict(passed=True,actual_result=actual,asan_ubsan=True,real_pthreads=True,commands=commands,
    compile_only_attempt01_preserved='test-attempt-01-result.json',
    unused_parameter_warning_disabled='matches kernel policy; original unchanged notifier event argument is unused',
    tested_files={n:sha(HERE/n) for n in names},private_binary=str(OUT/'test-budget'),private_binary_sha256=sha(OUT/'test-budget'),
    scope='actual old/new budget and system-PM wrapper functions plus actual provider setter/PM; real blocked worker thread and pthread join; discovery/workqueue/PSY and hardware are fake; no real system PM or kernel async execution',
    old_suites_rerun=False,device_SDK_build_or_shared_tree_accessed=False)
(HERE/'test-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(passed=True,cases=20,test_result_sha256=sha(HERE/'test-result.json'))))
