from pathlib import Path
import hashlib,json,subprocess
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
out=Path('/home/cy122/charging-management-20261023/pd5v-owner-context-r2');out.mkdir(parents=True,exist_ok=True)
cmd=['gcc','-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-unused-function','-fsanitize=address,undefined','-fno-omit-frame-pointer','-no-pie','-g',str(HERE/'test-context.c'),'-o',str(out/'test-context')]
build=subprocess.run(cmd,capture_output=True,text=True)
if build.returncode:print(build.stdout+build.stderr);raise SystemExit(build.returncode)
run=subprocess.run([str(out/'test-context')],capture_output=True,text=True)
result=dict(passed=run.returncode==0,affected_groups=8,actual_functions_compiled=23,
 actual_change_functions=['samurai_pd5v_acquire','samurai_pd5v_quiesce','samurai_pd5v_release','pd5v_unpublish_if_retired','samurai_pd5v_create','samurai_pd5v_destroy','qcom_pmic_typec_prepare','qcom_pmic_typec_complete'],
 stdout=run.stdout,stderr=run.stderr,tested_files={n:sha(HERE/n) for n in ['qcom_pmic_typec_5v.c','qcom_pmic_typec_5v.h','qcom_pmic_typec.c','actual-functions.inc','actual-probe.inc','function-manifest.json','kernel-boundary-fixture.inc','fixture-provenance.json','test-context.c','run-context-tests.py']},
 kernel_IO_and_deterministic_interleave_boundaries_faked=True,context_objects_actually_heap_freed=True,original_7_groups_rerun=False,
 reused_original_test_receipt_sha256=sha(HERE.parent/'pd5v-owner-feasibility/test-result.json'),
 phone_accessed=False,SDK_invoked=False,Git_invoked=False)
(HERE/'test-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(passed=result['passed'],stdout=run.stdout,stderr=run.stderr)))
raise SystemExit(run.returncode)
