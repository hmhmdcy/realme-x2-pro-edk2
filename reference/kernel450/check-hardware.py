from pathlib import Path
import sys
import json
import host
HERE=Path(__file__).resolve().parent
attempt=sys.argv[1] if len(sys.argv)>1 else 'r3';assert attempt in ['r3','r4']
witnesses=[json.loads(p.read_text()) for p in host.PRIVATE.glob('live-'+attempt+'-*-private.json')]
witnesses=[v for v in witnesses if v.get('actual_candidate_core_mapping') and v.get('actual_isolated_ipa_uid10000_capabilities0') and v.get('uid')==10000 and v.get('effective_capabilities')==0]
assert witnesses,'A real live application and isolated IPA identity/mapping witness is required'
source=(HERE.parent/'kernel449/check-long.py').read_text().replace('stage=449','stage=450')
source=source.replace('production448_source_artifacts_and_factory_tuning_reused=True','candidate450_core_and444_ipa_proxy_with_factory443_tuning=True')
source=source.replace('r2_ipe_completed=physical','ipe_completed=physical')
source=source.replace("HERE/'lifecycle-validation.json'","HERE.parent/'kernel449/lifecycle-validation.json'")
source=source.replace("'runtime-collected-r2'",repr('runtime-collected-'+attempt)).replace("HERE/'residual-r2-validation.json'","HERE/"+repr('residual-'+attempt+'-validation.json'))
exec(compile(source,str(HERE/'check-hardware.py'),'exec'))
assert r['passed'] and all(not row['duplicate_negative_receipts'] and row['raw_strict_receipt_contract_passed'] for row in r['rows'])
r.update(attempt=attempt,raw_strict_receipts_passed=True,no_negative_enoent_duplicate_receipts=True,only_stats_retirement_changed=True,retained_lifecycle_results_are_baseline449=True,live_actual_candidate_mapping_and_user_ipa_identity_witnesses=len(witnesses),retained450_r2_camera_cancellation_frames=94)
(HERE/'hardware-validation.json').write_text(json.dumps(r,indent=2)+'\n')
