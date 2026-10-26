from pathlib import Path
import hashlib,json,subprocess
import storage
HERE=Path(__file__).resolve().parent;state=json.loads((HERE/'source-state.json').read_text())
tree=storage.candidate()/'src/libcamera-v0.7.2';base=Path(state['baseline']);patch=bytearray()
for name in state['changed_sources']:
 before=base/name;after=tree/name
 q=subprocess.run(['diff','-u','--label','a/'+name,'--label','b/'+name,str(before) if before.exists() else '/dev/null',str(after)],capture_output=True)
 assert q.returncode in [0,1],q.stderr.decode();patch.extend(q.stdout)
(HERE/'0037-camss-static-ife-gamma.patch').write_bytes(patch)
state.update(source_sha256={n:hashlib.sha256((tree/n).read_bytes()).hexdigest() for n in state['changed_sources']},
 built=not json.loads((HERE/'build-validation.json').read_text())['exit_code'],
 aarch64_contract_passed=json.loads((HERE/'ipa-contract-validation.json').read_text())['passed'])
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
print('Saved optional Gamma patch against released342 source; factory and unit values remain private.')
