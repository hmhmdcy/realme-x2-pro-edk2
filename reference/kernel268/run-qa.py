"""Run three finite offline checks and retain every command result."""
from pathlib import Path
import json
import subprocess
import time

R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel268')
state=dict(stage=268,phase='starting',terminal=False)
for name in ['inspect-full-features.py','collect-forward-packages.py','host-runtime-qa.py']:
    state['phase']=name;(P/'qa-state-private.json').write_text(json.dumps(state)+'\n')
    with (P/(name+'-orchestration-private.log')).open('xb') as log:
        q=subprocess.run(['python3',str(R/name)],stdout=log,stderr=subprocess.STDOUT)
    if q.returncode:
        state.update(terminal=True,exit_code=q.returncode);(P/'qa-state-private.json').write_text(json.dumps(state)+'\n')
        raise RuntimeError('QA failed: '+name)
state.update(phase='terminal',terminal=True,exit_code=0);(P/'qa-state-private.json').write_text(json.dumps(state)+'\n')
report=dict(stage=268,all_13_package_signatures_and_features_checked=True,
 all_five_ipa_signatures_checked_with_new_core=True,arm_tools_qcam_python_entrypoints_checked=True,
 source_cache_and_sdk_restored=True,phone_not_modified_by_qa=True)
(R/'complete-host-qa-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
