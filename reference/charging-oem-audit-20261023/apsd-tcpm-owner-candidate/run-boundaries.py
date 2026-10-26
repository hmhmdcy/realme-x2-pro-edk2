"""Only the nine extracted existing functions, fake OS/regmap, no old suites."""
from pathlib import Path
import hashlib,json,subprocess
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
out=Path('/home/cy122/charging-management-20261023/apsd-tcpm-owner-candidate');out.mkdir(exist_ok=True)
cmd=['gcc','-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-fsanitize=address,undefined','-fno-omit-frame-pointer','-no-pie','-g',str(HERE/'test-boundaries.c'),'-o',str(out/'boundary-test')]
build=subprocess.run(cmd,capture_output=True,text=True)
if build.returncode:print(build.stdout+build.stderr);raise SystemExit(build.returncode)
run=subprocess.run([str(out/'boundary-test')],capture_output=True,text=True)
result=dict(passed=run.returncode==0,existing_actual_functions=9,groups=5,stdout=run.stdout,stderr=run.stderr,
 compiled_with=cmd[:10],new_gate_policy_implemented=False,kernel_patch_created=False,
 production_object_built=False,old_suites_rerun=False,device_accessed=False,SDK_invoked=False,Git_invoked=False,
 tested_files={n:sha(HERE/n) for n in ['actual-functions.inc','function-manifest.json','test-boundaries.c','run-boundaries.py']})
(HERE/'test-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(passed=result['passed'],groups=5,actual_functions=9,stderr=run.stderr)))
raise SystemExit(run.returncode)
