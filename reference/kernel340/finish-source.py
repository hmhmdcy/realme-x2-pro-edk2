from pathlib import Path
import json,subprocess
import storage
HERE=Path(__file__).resolve().parent;state=json.loads((HERE/'source-state.json').read_text());tree=storage.candidate()/'src/libcamera-v0.7.2';base=Path(state['baseline']);patch=bytearray()
for name in state['changed_sources']:
 q=subprocess.run(['diff','-u','--label','a/'+name,'--label','b/'+name,str(base/name),str(tree/name)],capture_output=True);assert q.returncode in [0,1],q.stderr.decode();patch.extend(q.stdout)
(HERE/'0035-camss-runtime-aec-colour-correction.patch').write_bytes(patch)
for name in ['ipa-contract-validation.json','reference-regression-validation.json','runtime-ccm-validation.json','final-state-validation.json']:assert json.loads((HERE/name).read_text())['passed']
state.update(built=True,actual_aarch64_ipa_verified=True,four_camera_runtime_ccm_verified=True,static_lsc_reference_ccm_compatibility_verified=True,installed=False)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
# Clarify the experiment's enable override in the report without rerunning
# unchanged component checks just to edit a descriptive JSON field.
p=HERE/'ipa-contract-validation.json';d=json.loads(p.read_text());cases=json.loads(Path('/mnt/e/edk2-samurai-out/kernel340/profiles-private.json').read_text())
for row in d['cases']:
 if row['case'] in cases:
  row.setdefault('ccm_enabled',row['factory_ccm_enabled']);row['factory_ccm_enabled']=cases[row['case']]['item']['factory_ccm_enabled']
p.write_text(json.dumps(d,indent=2)+'\n')
print('Saved340 component patch against339; candidate and deployed sources remain separate.')
