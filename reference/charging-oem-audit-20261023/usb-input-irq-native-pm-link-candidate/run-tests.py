"""Only the eight new PM-link/IRQ probe combinations; no kernel storage/build."""
from pathlib import Path
import hashlib,json,subprocess,time
HERE=Path(__file__).resolve().parent
OUT=Path('/home/cy122/charging-management-20261023/usb-input-irq-native-pm-link-tests-02')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=json.loads((HERE/'source-result.json').read_bytes())
assert source['passed'] and sha(HERE/'samurai-usb-input.c')==source['source_sha256']
for name,pin in source['extracts'].items():assert sha(HERE/name)==pin
assert not OUT.exists();OUT.mkdir(mode=0o700)
commands=[]
for label,argv in [('compile',['gcc','-std=c11','-O1','-g','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-sign-compare','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(HERE/'test-merge.c'),'-o',str(OUT/'test-merge')]),('test',[str(OUT/'test-merge')])]:
    child=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    try: stdout,stderr=child.communicate()
    finally: rc=child.wait()
    (OUT/(label+'-stdout-private.txt')).write_bytes(stdout);(OUT/(label+'-stderr-private.txt')).write_bytes(stderr)
    commands.append(dict(label=label,argv=argv,pid=child.pid,terminal=True,returncode=rc,stdout_sha256=hashlib.sha256(stdout).hexdigest(),stderr_sha256=hashlib.sha256(stderr).hexdigest()))
    if rc or stderr:
        (HERE/'test-attempt-result.json').write_text(json.dumps(dict(passed=False,commands=commands),indent=2)+'\n')
        raise RuntimeError((rc,stderr.decode(errors='replace')))
actual=json.loads(stdout);assert actual['passed'] and actual['actual_function_cases']==8
files=['samurai-usb-input.c','samurai-usb-input-decode.h','native-pm-link.c.inc','actual-link-irq-probe.inc','actual-pm-and-setter.inc','actual-dwc-vbus-work.inc','test-merge.c','prepare-test.py','test-main.c.inc','run-tests.py']
r=dict(passed=True,actual_result=actual,asan_ubsan=True,commands=commands,tested_files={name:sha(HERE/name) for name in files},private_binary=str(OUT/'test-merge'),private_binary_sha256=sha(OUT/'test-merge'),old21_or_IRQ16_rerun=False,hardware_or_systemPM_or_kernel_build_verified=False)
(HERE/'test-result.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(dict(passed=True,cases=8,test_result_sha256=sha(HERE/'test-result.json'))))
