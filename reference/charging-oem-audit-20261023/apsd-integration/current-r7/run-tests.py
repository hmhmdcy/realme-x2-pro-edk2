"""Only current API boundary fixture; no old OEM/Float test repetition."""
from pathlib import Path
import hashlib
import json
import subprocess

HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
prepare=subprocess.run(['python3',str(HERE/'prepare-function-fixture.py')],capture_output=True,check=True)
flags=['-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-fsanitize=address,undefined','-fno-omit-frame-pointer']
compiler=subprocess.run(['gcc',*flags,str(HERE/'test-api-boundaries.c'),'-o',str(HERE/'test-api-boundaries')],capture_output=True)
run=subprocess.run([str(HERE/'test-api-boundaries')],capture_output=True) if compiler.returncode==0 else None
result=dict(passed=compiler.returncode==0 and run is not None and run.returncode==0,actual_api_groups=6,
 functions=10,flags=flags,compile_returncode=compiler.returncode,compile_stderr=compiler.stderr.decode(),
 runtime_returncode=run.returncode if run else None,runtime_stdout=run.stdout.decode() if run else '',
 runtime_stderr=run.stderr.decode() if run else '',
 sha256={n:sha(HERE/n) for n in ['actual-functions.inc','function-manifest.json','test-api-boundaries.c']},
 phone_accessed=False,ssh_executed=False,sdk_invoked=False,driver_patch_created=False,
 old_oem_float_tests_repeated=False,scope='unchanged actual functions with fake OS objects; proves API limitations, not hardware safety')
(HERE/'test-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
raise SystemExit(0 if result['passed'] else 1)
