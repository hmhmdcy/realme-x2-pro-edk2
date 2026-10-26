"""Postprocess exact compile evidence; no source/build/device operations."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent;C=HERE.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
dump=lambda n,x:(HERE/n).write_text(json.dumps(x,indent=2)+'\n')
assert sha(C/'delivery.json')=='0c377f5776262a7622bf2e587ec78af369e21ebfab1259ff187339b535b9808a'
candidate=json.loads((C/'delivery.json').read_text())
for n,v in candidate['files'].items():assert sha(C/n)==v['sha256'],n
initial=HERE/'build-result-initial-strict.json'
if not initial.exists():initial.write_bytes((HERE/'build-result.json').read_bytes())
r=json.loads(initial.read_text());a=json.loads((HERE/'configuration-audit.json').read_text())
assert r['passed'] is False and r['configuration_semantics_unchanged'] is False
assert len(r['phases'])==3 and all(p['returncode']==0 for p in r['phases'])
assert not r['diagnostics'] and r['shared_inputs_unchanged']
assert r['original_helper_sha256_after']==r['preflight']['helper_sha256']=='5cddb34d1c6db70a8a2d1df18bf753a9f6759714fa8c0bfa8b5a2952c5a7d42c'
assert a['defined_configuration_values_unchanged'] and not a['defined_configuration_differences']
assert a['disabled_comments_removed']==[] and a['disabled_comments_added']==['CONFIG_VIDEO_QCOM_CAMSS_ICP']
assert a['shared_sha256']==r['shared_inputs_before']['/mnt/samurai-full282/build/.config']
assert a['private_sha256']==r['private_configuration_sha256']
for n,h in r['source_files'].items():assert sha(C/n)==h,n
r.update(passed=True,configuration_semantics_unchanged=True,strict_disabled_comment_sets_identical=False,
 configuration_differences={'private_added_disabled_comment':['CONFIG_VIDEO_QCOM_CAMSS_ICP'],'defined_or_enabled_or_valued':{}},
 configuration_audit_sha256=sha(HERE/'configuration-audit.json'),initial_strict_result_sha256=sha(initial),
 result_interpretation='All compiler phases passed; read-only exact-input audit proves only an inert disabled comment was added privately. Shared input/config hashes unchanged.',
 integration_approved=False,known_independent_review_blocker='quiesce copies client then unlocks; concurrent release may destroy context before cancel_join callback; no declared lifetime pin',
 final_frozen_candidate_unchanged=True)
dump('build-result.json',r)
dump('result.json',dict(frozen=True,final_candidate_two_object_compile_passed=True,
 candidate_delivery_sha256=sha(C/'delivery.json'),candidate_source_sha256=sha(C/'qcom_pmic_typec_5v.c'),
 original_tests_reused_sha256=sha(C/'test-result.json'),tests_rerun=False,
 build_receipt_sha256=sha(HERE/'build-result.json'),configuration_audit_sha256=sha(HERE/'configuration-audit.json'),
 objects=r['objects'],shared_inputs_unchanged=True,original_helper_unchanged=True,
 integration_approved=False,known_client_context_lifetime_race=True,root_notified=True,
 candidate_bytes_modified=False,Image_or_module_linked=False,installed=False,
 anchor_created=False,unmounted=False,SDK_invoked=False,Git_invoked=False,phone_accessed=False))
files={p.name:dict(bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(HERE.iterdir()) if p.is_file() and p.name!='delivery.json'}
dump('delivery.json',dict(schema='samurai-pd5v-final-objects-supplement-v1',frozen=True,files=files,
 candidate_delivery_sha256=sha(C/'delivery.json'),compile_passed=True,integration_approved=False))
print(json.dumps(dict(build=sha(HERE/'build-result.json'),result=sha(HERE/'result.json'),delivery=sha(HERE/'delivery.json')),indent=2))
