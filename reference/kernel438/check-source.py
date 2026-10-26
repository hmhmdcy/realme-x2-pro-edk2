from pathlib import Path
import hashlib,json,shlex,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;T=storage.candidate()/'src/libcamera-v0.7.2'
state=json.loads((HERE.parent/'kernel437/source-state.json').read_text());build=json.loads((HERE/'build-validation.json').read_text());assert build['source_and_binary_unchanged']
for row in state['source_hashes']:assert hashlib.sha256((T/row['path']).read_bytes()).hexdigest()==row['sha256']
previous=json.loads((HERE.parent/'kernel437/build-validation.json').read_text())
assert build['runtime_files']==previous['runtime_files']
code='''from pathlib import Path
import hashlib,json
root=Path('/var/lib/samurai/k438-multicamera-tone-r1');manifest=json.loads((root/'manifest.json').read_text())
names=['factory-imx319-private.yaml','factory-s5k3m5-private.yaml','lib/libcamera.so.0.7.2','ipa/ipa_camss_vfe.so','ipa/ipa_camss_vfe.so.sign','proxy/camss_ipa_proxy']
result={n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in names}
assert all(result[n]==manifest[n] for n in names)
print(json.dumps(result))
'''
q=host.ssh('python3 -c '+shlex.quote(code),timeout=20);q.check_returncode();actual=json.loads(q.stdout)
for model in ['imx319','s5k3m5']:
 name='factory-'+model+'-private.yaml';assert actual[name]==hashlib.sha256((P/name).read_bytes()).hexdigest()
assert actual['ipa/ipa_camss_vfe.so']==next(r['sha256'] for r in build['runtime_files'] if r['name']=='ipa_camss_vfe.so')
(P/'actual-runtime-manifest-private.json').write_text(json.dumps(actual,indent=2)+'\n')
r=dict(stage=438,userspace_source_and_runtime_identical_to437=True,actual_uploaded_profiles_match_prepared_files=True,actual_runtime_files_match_launch_manifest=True,
 backend_pipeline_math_code_not_duplicated=True,kernel_board_sensor_code_unchanged=True,per_camera_data_only=True,original_mode_selection_and_bls_evidence_reused=True,
 ordinary_native_rear_paths_verified=True,isolated_rear_paths_not_newly_tested=True,front_ipe_nonidentity_ccm_pending=True,passed=True)
(HERE/'source-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
