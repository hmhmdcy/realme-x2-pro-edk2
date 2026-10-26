"""Save the generic source delta; never include selected factory tuning."""
from pathlib import Path
import difflib,hashlib,json,shutil
import storage
HERE=Path(__file__).resolve().parent
for name in ['ipa-contract-validation.json','agc-regression-validation.json']:
    assert json.loads((HERE/name).read_text())['passed']
assert json.loads((HERE/'build-validation.json').read_text())['exit_code']==0
tree=storage.candidate()/'src/libcamera-v0.7.2';baseline=tree.parents[2]/'libcamera342-r27-built/src/libcamera-v0.7.2'
names=['include/libcamera/ipa/camss.mojom','src/ipa/camss-vfe/camss.cpp',
 'src/ipa/camss-vfe/exposure_program.cpp','src/ipa/camss-vfe/exposure_program.h',
 'src/ipa/camss-vfe/hardware_agc.cpp','src/ipa/camss-vfe/hardware_agc.h','src/ipa/camss-vfe/meson.build',
 'src/ipa/libipa/aec_antibanding.cpp','src/ipa/libipa/aec_antibanding.h',
 'src/ipa/libipa/aec_exposure_table.cpp','src/ipa/libipa/aec_exposure_table.h',
 'src/ipa/libipa/agc_mean_luminance.cpp','src/ipa/libipa/agc_mean_luminance.h','src/ipa/libipa/meson.build',
 'src/libcamera/pipeline/camss-vfe/camss_vfe.cpp']
patch=[];records=[]
for name in names:
    source=tree/name;old=baseline/name;before=old.read_text() if old.exists() else '';after=source.read_text();assert before!=after,name
    patch.extend(difflib.unified_diff(before.splitlines(keepends=True),after.splitlines(keepends=True),fromfile='a/'+name if old.exists() else '/dev/null',tofile='b/'+name))
    records.append(dict(path=name,sha256=hashlib.sha256(source.read_bytes()).hexdigest(),baseline_sha256=hashlib.sha256(old.read_bytes()).hexdigest() if old.exists() else None))
for name in ['camss.cpp','hardware_agc.cpp','hardware_agc.h','exposure_program.cpp','exposure_program.h']:
    shutil.copyfile(tree/'src/ipa/camss-vfe'/name,HERE/'ipa'/name)
(HERE/'exposure-program-integration.patch').write_text(''.join(patch))
state=dict(stage=359,source=str(tree),baseline=str(baseline),baseline_installed_package_stage=342,
    changed=names,files=records,patch_sha256=hashlib.sha256((HERE/'exposure-program-integration.patch').read_bytes()).hexdigest(),
    current_native_ipa_contract_passed=True,common_agc_regression_passed=True,ipc_pipeline_version=1,
    current_isolated_ipc_verified=False,hardware_exercised=False,
    runtime_default_profiles_unchanged=True,full_gamma_candidate_349_merge_pending=True,
    installed=False,full_camera_goal_status='active')
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
print(json.dumps(dict(stage=359,changed_files=len(names),patch_bytes=(HERE/'exposure-program-integration.patch').stat().st_size,installed=False)))
