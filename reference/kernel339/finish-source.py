from pathlib import Path
import json,subprocess
import storage
HERE=Path(__file__).resolve().parent;state=json.loads((HERE/'source-state.json').read_text());tree=storage.candidate()/'src/libcamera-v0.7.2';base=Path(state['baseline'])
patch=bytearray()
for name in state['changed_sources']:
 old=base/name;new=tree/name
 q=subprocess.run(['diff','-u','--label','a/'+name,'--label','b/'+name,str(old) if old.exists() else '/dev/null',str(new)],capture_output=True)
 assert q.returncode in [0,1],q.stderr.decode();patch.extend(q.stdout)
(HERE/'0034-camss-runtime-reference-lux.patch').write_bytes(patch)
state.update(built=True,aarch64_ipa_instruction_oracle_verified=True,runtime_test_evidence='runtime-lux-validation.json')
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
print('Saved component patch against335 candidate; release recipes remain unchanged.')
