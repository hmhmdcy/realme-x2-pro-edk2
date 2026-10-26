"""Reuse the actually exercised R2 recovery, changing only trial identities."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'tcpm-sink-shutdown-candidate'
sha=lambda b:hashlib.sha256(b).hexdigest()
root_old='tcpm507-trial-20261025-02';root_new='tcpm508-trial-20261025-01'
helper_old='tcpm507-boot-guard.py';helper_new='tcpm508-boot-guard.py'
guard=(OLD/'boot-guard.py').read_text()
changes={root_old:root_new,helper_old:helper_new,'#507 SMP PREEMPT':'#508 SMP PREEMPT'}
new=guard
for a,b in changes.items():assert a in new;new=new.replace(a,b)
restored=new
for a,b in changes.items():restored=restored.replace(b,a)
assert restored==guard
assert not (HERE/'boot-guard.py').exists();(HERE/'boot-guard.py').write_text(new)
(HERE/'guard-equivalence-result.json').write_text(json.dumps({'passed':True,'identity_literal_changes':changes,
 'baseline_sha256':sha(guard.encode()),'source_sha256':sha(new.encode()),'all_other_source_bytes_exact':True,
 'algorithm_actual_R2_autorestore_verified':True,'new508_hardware_verified':False},indent=2)+'\n')
stage=(OLD/'trial-stage.py').read_text()
for a,b in {root_old:root_new,helper_old:helper_new,
 'precharge506-live-20261025-02':'precharge506-live-20261025-03',
 '[(11217,275499),(11218,275509),(11223,275599),(11224,275599),(11225,275600),(18739,643837)]':
 '[(7491,92596),(7492,92608),(7505,93199),(7506,93199),(7507,93199)]'}.items():
 assert a in stage;stage=stage.replace(a,b)
(HERE/'trial-stage.py').write_text(stage)
boot=json.loads((HERE/'boot-package-result.json').read_bytes());fat=json.loads((HERE/'logdump-package-result.json').read_bytes())
assert boot['passed'] and fat['passed']
build=json.loads((HERE/'build-result.json').read_bytes());tests=json.loads((HERE/'test-result.json').read_bytes())
assert build['passed'] and tests['passed']
for path,digest in build['build']['sources'].items():
 name=json.loads((HERE/'source.json').read_bytes())['sources'][path]['file']
 assert tests['source_sha256'][name]==digest==sha((HERE/name).read_bytes())
(HERE/'full-pd-shutdown-ready.json').write_text(json.dumps({'passed':True,
 'parts':{'boot':boot['boot_sha256'],'logdump':fat['candidate']['sha256']},
 'fixed_5V_only':True,'R2_shutdown_sources_unchanged_except_USB_budget_port':True,
 'new_USB_budget_tests_and_Image_passed':True,'guard_equivalent_to_actual_R2':True,
 'hardware_verified':False,'formal_adoption_allowed':False},indent=2)+'\n')
print('prepared guard, stage and fixed5V readiness; no phone operation')
