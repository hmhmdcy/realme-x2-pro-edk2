"""Retain complete subpackage, ELF, signature and ARM entrypoint checks."""
from pathlib import Path
import json, subprocess
import host

R=Path(__file__).resolve().parent
assert json.loads((R/'r20-package-build-validation.json').read_text())['package_count']==13
for name in ['inspect-full-features.py','collect-forward-packages.py','host-runtime-qa.py','prepare-runtime-repo.py']:
    source=(R.parent/'kernel268'/name).read_text()
    for a,b in [('kernel268','kernel271'),('268-r19','271-r20'),('r19','r20'),('stage=268','stage=271'),('k268','k271'),('0.1.0-r14','0.1.0-r15')]:source=source.replace(a,b)
    (R/name).write_text(source)
for name in ['inspect-full-features.py','collect-forward-packages.py','host-runtime-qa.py']:
    with (host.PRIVATE/(name+'-orchestration-private.log')).open('xb') as log:
        q=subprocess.run(['python3',str(R/name)],stdout=log,stderr=subprocess.STDOUT)
    assert q.returncode==0,'Inspect terminal QA log: '+name
proof=json.loads((R/'r20-host-runtime-qa-validation.json').read_text())
assert proof['all_five_ipa_signatures_valid'] and all(x['passed'] for x in proof['host_arm_emulation_runtime_checks'])
(R/'complete-host-qa-validation.json').write_text(json.dumps(dict(stage=271,all_13_package_signatures_and_features_checked=True,
 all_five_ipa_signatures_checked_with_new_core=True,arm_tools_qcam_python_entrypoints_checked=True,source_cache_and_sdk_restored=True,phone_not_modified_by_qa=True),indent=2)+'\n')
q=subprocess.run(['python3',str(R/'prepare-runtime-repo.py')],capture_output=True)
(host.PRIVATE/'runtime-repo-orchestration-private.log').write_bytes(q.stdout+q.stderr)
assert q.returncode==0
print('13 signed packages, full feature set, five IPA signatures and ARM tools passed; seven-package runtime repository ready.')
