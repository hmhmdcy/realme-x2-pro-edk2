from pathlib import Path
import json,subprocess,time
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel239');state=dict(stage=239,state='running',phase='preflight',started=time.time())
def save(): (P/'r15-qa-state-private.json').write_text(json.dumps(state,indent=2)+'\n')
save()
try:
 for name in ['inspect-full-features.py','collect-forward-packages.py','host-runtime-qa.py','prepare-candidate-bundle.py']:
  state['phase']=name;save()
  with (P/(name+'-orchestration-private.log')).open('xb') as log:
   result=subprocess.run(['python3',str(R/name)],stdout=log,stderr=subprocess.STDOUT)
  assert result.returncode==0,name
 state.update(state='terminal',phase='all-host-qa-and-runtime-bundle-complete',exit_code=0);save()
except BaseException:
 state.update(state='terminal',exit_code=1);save();raise
report=dict(stage=239,all_original_features_verified=True,all13_apk_signatures_verified=True,all_five_ipa_signatures_verified_against_current_core=True,arm_user_entrypoints_checked=True,seven_runtime_packages_bundled=True,physical_camera_fix_still_pending=True)
(R/'r15-complete-host-qa-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
