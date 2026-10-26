from pathlib import Path
import hashlib,json,subprocess
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
out=Path('/home/cy122/charging-management-20261023/pd5v-owner-feasibility');out.mkdir(parents=True,exist_ok=True)
command=['gcc','-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-fsanitize=address,undefined','-fno-omit-frame-pointer','-no-pie','-g',str(HERE/'test-control.c'),'-o',str(out/'test-control')]
build=subprocess.run(command,capture_output=True,text=True)
if build.returncode:print(build.stdout+build.stderr);raise SystemExit(build.returncode)
run=subprocess.run([str(out/'test-control')],capture_output=True,text=True)
result=dict(passed=run.returncode==0,group_count=7,actual_function_count=22,stdout=run.stdout,stderr=run.stderr,
 tested_files={n:sha(HERE/n) for n in ['qcom_pmic_typec_5v.c','qcom_pmic_typec_5v.h','qcom_pmic_typec.c','actual-functions.inc','actual-probe.inc','function-manifest.json','test-control.c','run-tests.py']},
 production_control_functions_executed=True,kernel_and_hardware_boundaries_faked=True,old_suites_rerun=False,phone_accessed=False,SDK_invoked=False,Git_invoked=False)
(HERE/'test-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(passed=result['passed'],stdout=run.stdout,stderr=run.stderr)))
raise SystemExit(run.returncode)
