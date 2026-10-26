"""Record the exact combined candidate and preserve a reproducible source delta."""
from pathlib import Path
import difflib,hashlib,json,shutil
import storage
HERE=Path(__file__).resolve().parent
for name in ['merge-validation.json','package-source-validation.json','ipa-contract-validation.json','package-build-validation.json','package-artifact-validation.json']:
    assert json.loads((HERE/name).read_text())['passed'],name
tree=storage.candidate()/'src/libcamera-v0.7.2';base=tree.parents[2]/'libcamera342-r27-built/src/libcamera-v0.7.2'
records=json.loads((HERE/'package-source-validation.json').read_text())['source_files'];patch=[]
for row in records:
    name=row['path'];after=tree/name;before=base/name;assert hashlib.sha256(after.read_bytes()).hexdigest()==row['sha256'],name
    patch.extend(difflib.unified_diff(before.read_text().splitlines(keepends=True) if before.exists() else [],after.read_text().splitlines(keepends=True),fromfile='a/'+name if before.exists() else '/dev/null',tofile='b/'+name))
for stage,names in [(349,['src/ipa/libipa/gamma_curve.cpp','src/ipa/camss-vfe/gamma_profile.cpp','src/ipa/camss-vfe/parameter_encoder.cpp']),
                    (359,['src/ipa/libipa/agc_mean_luminance.cpp','src/ipa/libipa/aec_exposure_table.cpp','src/ipa/libipa/aec_antibanding.cpp','src/ipa/camss-vfe/hardware_agc.cpp','src/ipa/camss-vfe/exposure_program.cpp'])]:
    parent=tree.parents[2]/('libcamera349-gamma-built' if stage==349 else 'libcamera359-exposure-built')/'src/libcamera-v0.7.2'
    for name in names:assert (tree/name).read_bytes()==(parent/name).read_bytes(),name
(HERE/'combined-r28-against-r27.patch').write_text(''.join(patch));shutil.copyfile(tree/'src/ipa/camss-vfe/camss.cpp',HERE/'camss-after.cpp')
report=dict(stage=360,source=str(tree),baseline=str(base),parent_candidates=[349,359],package_version='99990.7.2-r28',configuration_version='0.1.0-r23',
    source_files=records,patch_sha256=hashlib.sha256((HERE/'combined-r28-against-r27.patch').read_bytes()).hexdigest(),
    gamma_and_ae_algorithm_sources_unchanged_from_verified_parents=True,camss_pipeline_version=1,
    combined_aarch64_contract_passed=True,packaged_aarch64_contract_passed=True,isolated_ipc_current_version_verified=False,
    hardware_exercised=False,installed=False,full_camera_goal_status='active')
(HERE/'source-state.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(stage=360,source_files=len(records),combined_patch_bytes=(HERE/'combined-r28-against-r27.patch').stat().st_size,installed=False)))
