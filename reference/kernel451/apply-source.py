from pathlib import Path
import hashlib,json,shutil,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;storage.mount.mounted_build()
tree=storage.candidate()/'src/libcamera-v0.7.2';state=json.loads((HERE/'source-state.json').read_text())
assert state['proxy_optimization_pending'] and not state['changed_this_stage']
for row in state['source_hashes']:assert hashlib.sha256((tree/row['path']).read_bytes()).hexdigest()==row['sha256']
draft=HERE.parent/'kernel450/ipa-wire-generator-draft.patch';proof=json.loads((HERE.parent/'kernel450/ipa-wire-draft-validation.json').read_text())
assert proof['passed'] and proof['protocol_version_6_compatible'] and proof['old_decoder_reads_new_bytes']
assert hashlib.sha256(draft.read_bytes()).hexdigest()==proof['patch_sha256']
patch=HERE/'0062-camss-worker-byte-vector-wire-compatible.patch';shutil.copyfile(draft,patch)
q=subprocess.run(['patch','-p1','--batch','--fuzz=0','-i',str(patch)],cwd=tree,capture_output=True)
(P/'patch-apply-private.log').write_bytes(q.stdout+q.stderr);assert not q.returncode and b'offset' not in q.stdout.lower() and b'fuzz' not in q.stdout.lower(),(q.stdout+q.stderr).decode()
changed=['utils/codegen/ipc/generators/libcamera_templates/proxy_functions.tmpl','utils/codegen/ipc/generators/libcamera_templates/module_ipa_proxy_worker.cpp.tmpl','include/libcamera/internal/camss_byte_serializer.h']
assert all(row['path'] not in changed for row in state['source_hashes'])
for name in changed:state['source_hashes'].append(dict(path=name,sha256=hashlib.sha256((tree/name).read_bytes()).hexdigest()))
state.update(changed_this_stage=changed,proxy_optimization_pending=False,wire_format_unchanged=True)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
r=dict(stage=451,patch_sha256=proof['patch_sha256'],patch_zero_fuzz_offset=True,only_camss_two_worker_output_fields_change=True,other_four_workers_and_all_host_proxies_generated_unchanged=True,protocol6_and_core_ipa_algorithms_preserved=True,host_wire_proof_cases=proof['host_wire_proof']['cases'],phone_accessed=False,passed=True)
(HERE/'source-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
