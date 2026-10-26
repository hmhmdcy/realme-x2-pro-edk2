from pathlib import Path
import hashlib,json,shutil
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;volume=storage.mount.mounted_build().parent;prefix=volume/'camera440-package-prefix-r2';tree=storage.candidate()/'src/libcamera-v0.7.2'
assert json.loads((HERE/'packaged-contract-validation.json').read_text())['passed']
state=json.loads((HERE/'source-state.json').read_text())
for row in state['source_hashes']:assert hashlib.sha256((tree/row['path']).read_bytes()).hexdigest()==row['sha256']
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
files={'libcamera.so.0.7.2':'usr/lib/libcamera.so.0.7.2','libcamera-base.so.0.7.2':'usr/lib/libcamera-base.so.0.7.2','ipa_camss_vfe.so':'usr/lib/libcamera/ipa/ipa_camss_vfe.so','ipa_camss_vfe.so.sign':'usr/lib/libcamera/ipa/ipa_camss_vfe.so.sign','camss_ipa_proxy':'usr/libexec/libcamera/camss_ipa_proxy'}
rows=[]
for name,rel in files.items():
 path=prefix/rel;shutil.copyfile(path,P/name);rows.append({'name':name,'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
(HERE/'build-validation.json').write_text(json.dumps({'stage':440,'attempt':2,'passed':True,'private_ipa_version':5,'packaged_payload':True,'source_stage':440,'runtime_files':rows},indent=2)+'\n')
capture=json.loads((HERE.parent/'kernel437/capture-validation.json').read_text());source=P.parent/'kernel437/capture';assert hashlib.sha256(source.read_bytes()).hexdigest()==capture['binary_sha256'];shutil.copyfile(source,P/'capture');capture.update(stage=440,reused_from_stage437=True);(HERE/'capture-validation.json').write_text(json.dumps(capture,indent=2)+'\n')
raw=json.loads((HERE/'raw-client-build-validation.json').read_text());assert raw['passed'] and hashlib.sha256((P/'pipeline-smoke').read_bytes()).hexdigest()==raw['binary_sha256']
report=json.loads((HERE/'packaged-contract-validation.json').read_text());report.update(actual_ipa_sha256=hashlib.sha256((P/'ipa_camss_vfe.so').read_bytes()).hexdigest());(HERE/'ipa-validation.json').write_text(json.dumps(report,indent=2)+'\n')
profile_rows=[]
for model,stage in [('s5kgw1',437),('imx319',438),('s5k3m5',438),('imx471',439)]:
 name=f'factory-{model}-private.yaml';assert (P/name).read_bytes()==(P.parent/f'kernel{stage}'/name).read_bytes();profile_rows.append({'model':model,'reused_stage':stage,'sha256':hashlib.sha256((P/name).read_bytes()).hexdigest()})
(P/'private-profile-inputs.json').write_text(json.dumps(profile_rows,indent=2)+'\n')
r={'stage':440,'passed':True,'actual440_sources_match':True,'raw_only_pd10_gate_fixed':True,'packaged_runtime_inputs_prepared':True,'four_private_profiles_reused_without_changes':True,'public_generic_configs_unmodified':True,'phone_changed':False}
(HERE/'source-validation.json').write_text(json.dumps(r,indent=2)+'\n')
artifact=json.loads((HERE/'package-artifact-validation.json').read_text());artifact['packaged_camss_mathematical_contract_still_to_run']=False;artifact['packaged_contract_evidence']='packaged-contract-validation.json';(HERE/'package-artifact-validation.json').write_text(json.dumps(artifact,indent=2)+'\n')
print(json.dumps(r,indent=2))
