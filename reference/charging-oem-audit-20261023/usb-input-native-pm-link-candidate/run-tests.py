"""Run just the new actual-function boundary cases. No storage helper or build tree."""
from pathlib import Path
import hashlib, json, subprocess, time
HERE=Path(__file__).resolve().parent
OUT=Path('/home/cy122/charging-management-20261023/usb-input-native-pm-link-tests-01')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=json.loads((HERE/'source-result.json').read_bytes())
assert source['passed'] and sha(HERE/'samurai-usb-input.c')==source['source_sha256']
for name,pin in source['extracts'].items():assert sha(HERE/name)==pin
assert not OUT.exists();OUT.mkdir(mode=0o700)
commands=[]
for label,argv in [('compile',['gcc','-std=c11','-O1','-g','-Wall','-Wextra','-Werror',
        '-fsanitize=address,undefined','-fno-omit-frame-pointer',str(HERE/'test-native-pm.c'),'-o',str(OUT/'test-native-pm')]),
        ('test',[str(OUT/'test-native-pm')])]:
    start=time.monotonic();child=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    stdout,stderr=child.communicate();rc=child.wait()
    (OUT/(label+'-stdout-private.txt')).write_bytes(stdout);(OUT/(label+'-stderr-private.txt')).write_bytes(stderr)
    commands.append(dict(label=label,argv=argv,pid=child.pid,terminal=True,returncode=rc,seconds=time.monotonic()-start,
        stdout_sha256=hashlib.sha256(stdout).hexdigest(),stderr_sha256=hashlib.sha256(stderr).hexdigest()))
    if rc or stderr:
        (HERE/'test-attempt-result.json').write_text(json.dumps(dict(passed=False,commands=commands),indent=2)+'\n')
        raise RuntimeError((rc,stderr.decode(errors='replace')))
actual=json.loads(stdout);assert actual['passed'] and actual['actual_function_cases']==21
result=dict(passed=True,actual_result=actual,asan_ubsan=True,commands=commands,
    tested_files={n:sha(HERE/n) for n in ['samurai-usb-input.c','samurai-usb-input-decode.h','native-pm-link.c.inc',
        'actual-link-and-probe.inc','actual-pm-and-setter.inc','actual-dwc-vbus-work.inc','test-native-pm.c','run-tests.py']},
    private_binary_path=str(OUT/'test-native-pm'),private_binary_sha256=sha(OUT/'test-native-pm'),
    scope='actual provider functions/full probe body and original DWC vbus work; fake OF, driver-core/devres, PSY and workqueue boundaries; not real probe/system-PM or hardware validation',
    old_suites_rerun=False,device_or_SDK_or_Git_or_shared_build_accessed=False)
(HERE/'test-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(passed=True,cases=21,test_result_sha256=sha(HERE/'test-result.json'))))
