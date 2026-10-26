from pathlib import Path
import hashlib,json
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;volume=storage.mount.mounted_build().parent
tree=storage.candidate()/'src/libcamera-v0.7.2';state=json.loads((HERE.parent/'kernel448/source-state.json').read_text())
for row in state['source_hashes']:assert hashlib.sha256((tree/row['path']).read_bytes()).hexdigest()==row['sha256']
build=json.loads((HERE.parent/'kernel448/build-validation.json').read_text());assert build['passed'] and build['private_ipa_version']==6
files={}
for row in build['runtime_files']:
 p=P.parent/'kernel448'/row['name'];assert hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256']
 kind='lib/' if row['name'].startswith('libcamera') else 'proxy/' if row['name']=='camss_ipa_proxy' else 'ipa/'
 files[kind+row['name']]=dict(path=str(p),sha256=row['sha256'])
p=tree/'output/src/libcamera/base/libcamera-base.so.0.7.2';files['lib/libcamera-base.so.0.7.2']=dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
profile=P.parent/'kernel443/factory-s5kgw1-private.yaml';expected=json.loads((HERE.parent/'kernel443/profile-export-validation.json').read_text());assert hashlib.sha256(profile.read_bytes()).hexdigest()==expected['profile_sha256']
for proof in ['source','capacity','unprivileged','reentry']:
 assert json.loads((HERE.parent/'kernel448'/(proof+'-validation.json')).read_text())['passed']
kernel=json.loads((HERE.parent/'kernel441/kernel-source-state.json').read_text())
for row in kernel['source_hashes']:assert hashlib.sha256((volume/'source354'/row['path']).read_bytes()).hexdigest()==row['sha256']
(P/'runtime-input-files-private.json').write_text(json.dumps(files,indent=2)+'\n')
r=dict(stage=449,actual_448_source_and_artifacts_reused_without_changes=True,core_sha256=files['lib/libcamera.so.0.7.2']['sha256'],protocol6_signature_and_proxy_retained=True,stock443_mode4_profile_unchanged=True,retained441_module_source_unchanged=True,no_new_core_or_kernel_build=True,phone_accessed=False,passed=True)
(HERE/'runtime-inputs-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
