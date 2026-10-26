"""Verify actual candidate inputs, unchanged stock mode and IPA signature."""
from pathlib import Path
import ast,hashlib,json,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
volume=storage.mount.mounted_build().parent;tree=storage.candidate()/'src/libcamera-v0.7.2'
state=json.loads((HERE/'source-state.json').read_text())
for row in state['source_hashes']:assert hashlib.sha256((tree/row['path']).read_bytes()).hexdigest()==row['sha256']
kernel=json.loads((HERE/'kernel-source-state.json').read_text())
for row in kernel['source_hashes']:assert hashlib.sha256((volume/'source354'/row['path']).read_bytes()).hexdigest()==row['sha256']
old=volume/'libcamera440-release-r32/src/libcamera-v0.7.2'
for row in state['source_hashes']:
 if row['path'] not in state['changed_paths']:assert (tree/row['path']).read_bytes()==(old/row['path']).read_bytes()
files={}
build=json.loads((HERE/'build-validation.json').read_text())
for row in build['runtime_files']:
 p=P/row['name'];assert hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256']
 dest=('lib/' if row['name'].startswith('libcamera') else 'proxy/' if row['name']=='camss_ipa_proxy' else 'ipa/')+row['name']
 files[dest]=dict(path=str(p),sha256=row['sha256'])
p=tree/'output/src/libcamera/base/libcamera-base.so.0.7.2'
files['lib/libcamera-base.so.0.7.2']=dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
T='/work/libcamera/src/libcamera-v0.7.2'
with storage.sdk_candidate():
 q=subprocess.run(['chroot',str(storage.SDK),'env','LD_LIBRARY_PATH='+T+'/output/src/libcamera:'+T+'/output/src/libcamera/base',T+'/output/src/apps/ipa-verify/ipa_verify',T+'/output/src/ipa/camss-vfe/ipa_camss_vfe.so'],capture_output=True,timeout=40)
(P/'candidate-signature-private.log').write_bytes(q.stdout+q.stderr)
assert not q.returncode and b'IPA module signature is valid' in q.stdout
profile=P.parent/'kernel440/factory-s5kgw1-private.yaml'
assert profile.read_bytes()==(P.parent/'kernel437/factory-s5kgw1-private.yaml').read_bytes()
# Parse only own worker text; this neither starts a worker nor accesses the phone.
prefix=(HERE.parent/'kernel342/native-install.py').read_text().split('def versions():')[0]
body=(HERE.parent/'kernel434/capture-worker-body.py').read_text()
a=body.index(" state['captures']={}");z=body.index('\nexcept BaseException:',a)
ast.parse(prefix+'\n'+body[:a]+(HERE/'auto-capture-body.py').read_text()+body[z:])
(P/'runtime-input-files-private.json').write_text(json.dumps(files,indent=2)+'\n')
r=dict(stage=441,actual_userspace_and_kernel_source_hashes_match=True,only_four_pipeline_files_changed_vs440=True,ipa_math_protocol_and_profile_sources_unchanged=True,actual_candidate_ipa_signature_verified=True,private_stock_main_profile_reused_unchanged_from437_and440=True,worker_syntax_checked=True,phone_accessed=False,installed=False,passed=True)
(HERE/'runtime-inputs-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
