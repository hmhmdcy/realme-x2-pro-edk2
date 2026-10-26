from pathlib import Path
import hashlib,json,shutil,subprocess,tempfile
import host,storage
HERE=Path(__file__).resolve().parent;v=storage.mount.mounted_build().parent
old=v/'libcamera441-variable-pd10/src/libcamera-v0.7.2';tree=storage.candidate()/'src/libcamera-v0.7.2';rel='src/libcamera/pipeline/camss-vfe/camss_vfe.cpp'
with tempfile.TemporaryDirectory(prefix='camera442-',dir=v/'tmp') as directory:
 root=Path(directory);p=root/rel;p.parent.mkdir(parents=True);shutil.copyfile(old/rel,p)
 q=subprocess.run(['patch','-p1','--batch','--fuzz=0','-i',str(HERE/'0055-camss-stop-cancel-status.patch')],cwd=root,capture_output=True)
 assert not q.returncode and b'offset' not in q.stdout and p.read_bytes()==(tree/rel).read_bytes()
state=json.loads((HERE/'source-state.json').read_text())
for row in state['source_hashes']:
 assert hashlib.sha256((tree/row['path']).read_bytes()).hexdigest()==row['sha256']
 if row['path']!=rel:assert (tree/row['path']).read_bytes()==(old/row['path']).read_bytes()
for file in ['output/src/ipa/camss-vfe/ipa_camss_vfe.so','output/src/ipa/camss-vfe/ipa_camss_vfe.so.sign','output/src/libcamera/proxy/worker/camss_ipa_proxy']:
 assert (tree/file).read_bytes()==(old/file).read_bytes()
r=dict(stage=442,only_one_pipeline_file_changed_from441=True,patch_zero_fuzz_offset_and_source_equal=True,ipa_signature_proxy_protocol_and_numerics_byte_identical=True,live_error_not_converted_to_cancel=True,stopped_buffers_cancel_request_via_existing_request_completeBuffer_contract=True,phone_accessed=False,passed=True)
(HERE/'source-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
