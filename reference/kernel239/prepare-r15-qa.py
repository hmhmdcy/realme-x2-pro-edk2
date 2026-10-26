from pathlib import Path
import ast,json
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel239')
assert json.loads((R/'r15-package-build-validation.json').read_text())['package_count']==13
for name in ['inspect-full-features.py','collect-forward-packages.py','host-runtime-qa.py','prepare-candidate-bundle.py','stage-candidate.py']:
 text=(R.parent/'kernel238'/name).read_text().replace('kernel238','kernel239').replace('stage=238','stage=239').replace('238-r14','239-r15').replace('r14','r15').replace('k238','k239').replace('0.1.0-r9','0.1.0-r10').replace("'package-build-validation.json'","'r15-package-build-validation.json'")
 if name=='prepare-candidate-bundle.py':
  old="assert json.loads((R/'gain-helper-test-validation.json').read_text())['results']['r15']['exit']==0"
  assert text.count(old)==1
  new="helper=Path('/home/cy122/x2pro-linux/libcamera214-root/work/libcamera239-r15-built/src/libcamera-v0.7.2/src/ipa/libipa/camera_sensor_helper.cpp');assert hashlib.sha256(helper.read_bytes()).hexdigest()==json.loads((R.parent/'kernel238/helper-source-validation.json').read_text())['source_files']['src/ipa/libipa/camera_sensor_helper.cpp']"
  text=text.replace(old,new)
 if name=='stage-candidate.py':
  old="assert json.loads((r/'k239-vendor-audit/state-private.json').read_text())['exit_code']==0";assert text.count(old)==1
  text=text.replace(old,"assert json.loads((r/'k239-odm-source/state-private.json').read_text())['exit_code']==0")
  text=text.replace('installed_r13_unchanged=True','installed_r13_unchanged=True,initial_parameters_fix_not_yet_physically_verified=True')
 ast.parse(text);target=R/name
 if target.exists():assert target.read_text()==text,'Preserve a differing prepared script rather than overwrite'
 else:target.write_text(text)
state_path=P/'current-work-private.json';state=json.loads(state_path.read_text(encoding='utf-8-sig'));state.update(active_build_session=None,state='All13 r15/r10 packages built and original214/r14 restored; QA next',next='Run full feature/signature/runtime QA, stage r15 in RAM then verify initial parameters across stop/start; default r13 remains.');state_path.write_text(json.dumps(state,indent=2)+'\n')
print('239 full r15 QA and RAM stage prepared; r14 helper source unchanged')
