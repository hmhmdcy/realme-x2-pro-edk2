"""Only native-retain delta, actual extracted C body with fake OF boundary."""
from pathlib import Path
import hashlib,json,os,subprocess,time
HERE=Path(__file__).resolve().parent
OUT=Path('/home/cy122/charging-management-20261023/usb-input-flat-consumer-tests-01')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=json.loads((HERE/'source-result.json').read_bytes())
assert sha(HERE/'samurai-usb-input.c')==source['candidate_source_sha256']
assert sha(HERE/'actual-retain.inc')==source['actual_function_sha256']
assert not OUT.exists();OUT.mkdir(mode=0o700)
commands=[]
for argv,label in [(['gcc','-std=c11','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(HERE/'test-retain.c'),'-o',str(OUT/'test-retain')],'compile'),([str(OUT/'test-retain')],'test')]:
 started=time.monotonic();child=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 stdout,stderr=child.communicate();rc=child.wait()
 (OUT/(label+'-stdout-private.txt')).write_bytes(stdout);(OUT/(label+'-stderr-private.txt')).write_bytes(stderr)
 commands.append(dict(argv=argv,pid=child.pid,terminal=True,returncode=rc,seconds=time.monotonic()-started,stdout_sha256=hashlib.sha256(stdout).hexdigest(),stderr_sha256=hashlib.sha256(stderr).hexdigest()))
 assert rc==0 and not stderr,(rc,stderr.decode(errors='replace'))
actual=json.loads(stdout);assert actual==dict(actual_function_cases=11,passed=True)
result=dict(passed=True,actual_function_result=actual,asan_ubsan=True,commands=commands,
 tested_files={name:sha(HERE/name) for name in ('samurai-usb-input.c','samurai-usb-input-decode.h','actual-retain.inc','test-retain.c','run-tests.py')},
 private_binary_path=str(OUT/'test-retain'),private_binary_sha256=sha(OUT/'test-retain'),
 scope='actual retain function; OF available/compatible/property/ref and module/log interfaces fake; not full probe or real lifetime test',
 old_tests_rerun=False,device_or_SDK_or_Git_accessed=False)
(HERE/'test-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(passed=True,cases=11,test_result_sha256=sha(HERE/'test-result.json'))))
