from pathlib import Path
import hashlib,json,subprocess
HERE=Path(__file__).resolve().parent
OUT=Path('/home/cy122/charging-management-20261023/usbin-init-provider-candidate-tests');OUT.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
subprocess.run(['python3',str(HERE/'prepare-tests.py')],check=True)
flags=['-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-fsanitize=address,undefined','-fno-omit-frame-pointer','-no-pie']
binary=OUT/'test-provider'
p=subprocess.run(['gcc',*flags,str(HERE/'test-provider.c'),'-o',str(binary)],capture_output=True,text=True)
assert p.returncode==0,p.stderr
p=subprocess.run([str(binary)],capture_output=True,text=True)
assert p.returncode==0,(p.returncode,p.stdout,p.stderr)
groups=[s[4:] for s in p.stdout.splitlines() if s.startswith('ok: ')]
assert len(groups)==10 and not p.stderr
r=dict(passed=True,group_count=10,groups=groups,actual_functions=17,asan_ubsan=True,flags=flags,
 stdout=p.stdout,stderr=p.stderr,binary_private=str(binary),binary_sha256=sha(binary),
 files={n:sha(HERE/n) for n in ['samurai-usb-input.c','samurai-usb-input-decode.h','usbin-init-core.h','prepare-tests.py','test-provider.c','tested-functions.inc','tested-struct.inc','function-manifest.json','run-tests.py']},
 scope='new actual provider initialization, PM, worker and unchanged source/native functions; fake regmap/kernel boundary',
 old_helper_tests_rerun=False,old_float_suite_rerun=False,physical_test=False,phone_accessed=False,sdk_invoked=False)
(HERE/'test-result.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(dict(passed=True,groups=10,actual_functions=17)))
