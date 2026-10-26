from pathlib import Path
import ast,hashlib,json
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;volume=storage.mount.mounted_build().parent
tree=storage.candidate()/'src/libcamera-v0.7.2';state=json.loads((HERE/'source-state.json').read_text())
for row in state['source_hashes']:assert hashlib.sha256((tree/row['path']).read_bytes()).hexdigest()==row['sha256']
kernel=json.loads((HERE.parent/'kernel441/kernel-source-state.json').read_text())
for row in kernel['source_hashes']:assert hashlib.sha256((volume/'source354'/row['path']).read_bytes()).hexdigest()==row['sha256']
contract=json.loads((HERE/'focused-module-validation.json').read_text());assert contract['passed'] and contract['signature_verified']
build=json.loads((HERE/'build-validation.json').read_text());assert build['passed'] and build['private_ipa_version']==6
files={}
for row in build['runtime_files']:
 p=P/row['name'];assert hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256']
 dest=('lib/' if row['name'].startswith('libcamera') else 'proxy/' if row['name']=='camss_ipa_proxy' else 'ipa/')+row['name']
 files[dest]=dict(path=str(p),sha256=row['sha256'])
p=tree/'output/src/libcamera/base/libcamera-base.so.0.7.2'
files['lib/libcamera-base.so.0.7.2']=dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
profile=P.parent/'kernel443/factory-s5kgw1-private.yaml';expected=json.loads((HERE.parent/'kernel443/profile-export-validation.json').read_text())
assert hashlib.sha256(profile.read_bytes()).hexdigest()==expected['profile_sha256']
(P/'runtime-input-files-private.json').write_text(json.dumps(files,indent=2)+'\n')
r=dict(stage=444,actual_userspace_and_retained441_kernel_source_hashes_match=True,private_ipa_version=6,
 actual_candidate_ipa_signature_verified_in_module_contract=True,private443_mode4_stock_profile_reused_unchanged=True,
 runtime_artifact_hashes_match_build=True,phone_accessed=False,installed=False,passed=True)
(HERE/'runtime-inputs-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
