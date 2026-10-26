from pathlib import Path
import json,subprocess
import host
R=Path(__file__).resolve().parent
assert json.loads((R/'r23-package-build-validation.json').read_text())['package_count']==13
for name in ['inspect-full-features.py','collect-forward-packages.py','host-runtime-qa.py']:
 with (host.PRIVATE/(name+'-orchestration-private.log')).open('xb') as log:
  q=subprocess.run(['python3',str(R/name)],stdout=log,stderr=subprocess.STDOUT)
 assert q.returncode==0,'Inspect terminal QA log: '+name
proof=json.loads((R/'r23-host-runtime-qa-validation.json').read_text())
assert proof['all_five_ipa_signatures_valid'] and all(x['passed'] for x in proof['host_arm_emulation_runtime_checks'])
(R/'complete-host-qa-validation.json').write_text(json.dumps(dict(stage=277,all_13_package_signatures_and_features_checked=True,
 all_five_ipa_signatures_checked_with_new_core=True,arm_tools_qcam_python_entrypoints_checked=True,
 source_cache_and_sdk_restored=True,phone_not_modified_by_qa=True),indent=2)+'\n')
q=subprocess.run(['python3',str(R/'prepare-runtime-repo.py')],capture_output=True)
(host.PRIVATE/'runtime-repo-orchestration-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0
print('13 signed packages, full features, five IPA signatures and ARM entrypoints passed; seven-package repository ready.')
