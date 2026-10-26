from pathlib import Path
import json,subprocess
import storage
HERE=Path(__file__).resolve().parent;state=json.loads((HERE/'source-state.json').read_text());tree=storage.candidate()/'src/libcamera-v0.7.2';base=Path(state['baseline']);patch=bytearray()
for name in state['changed_sources']:
 old=base/name;q=subprocess.run(['diff','-u','--label','a/'+name,'--label','b/'+name,str(old) if old.exists() else '/dev/null',str(tree/name)],capture_output=True);assert q.returncode in [0,1],q.stderr.decode();patch.extend(q.stdout)
(HERE/'0036-camss-dynamic-lens-shading.patch').write_bytes(patch)
for name in ['ipa-contract-validation.json','reference-regression-validation.json','configuration-validation.json','control-method-validation.json','runtime-lsc-validation.json','final-state-validation.json']:assert json.loads((HERE/name).read_text())['passed'],name
state.update(built=True,aarch64_lsc_ccm_packet_bytes_verified=193160,dynamic_lsc_factory_unit_four_camera_verified=True,static_lsc_reference_ccm_compatible=True,front_factory_ccm_disabled_preserved=True,installed=False)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n');print('Saved341 dynamic LSC patch against340; verified source remains an uninstalled candidate.')
