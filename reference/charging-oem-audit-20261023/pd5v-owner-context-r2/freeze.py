"""Only local candidate/receipt freeze; no source volume or devices."""
from pathlib import Path
import difflib,hashlib,json
HERE=Path(__file__).resolve().parent;R1=HERE.parent/'pd5v-owner-feasibility'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
dump=lambda n,x:(HERE/n).write_text(json.dumps(x,indent=2)+'\n')
assert sha(R1/'delivery.json')=='0c377f5776262a7622bf2e587ec78af369e21ebfab1259ff187339b535b9808a'
old=json.loads((R1/'delivery.json').read_text())
for n,v in old['files'].items():assert sha(R1/n)==v['sha256'],n
t=json.loads((HERE/'test-result.json').read_text());b=json.loads((HERE/'build-result.json').read_text())
assert t['passed'] and t['affected_groups']==8 and not t['original_7_groups_rerun']
for n,h in t['tested_files'].items():assert sha(HERE/n)==h,n
assert b['passed'] and not b['diagnostics'] and b['shared_inputs_unchanged'] and b['configuration_semantics_unchanged'] and not b['configuration_differences']
for n,h in b['source_files'].items():assert sha(HERE/n)==h,n
patch=[]
for n in ['qcom_pmic_typec_5v.c','qcom_pmic_typec_5v.h']:
 patch.extend(difflib.unified_diff((R1/n).read_text().splitlines(True),(HERE/n).read_text().splitlines(True),fromfile='a/'+n,tofile='b/'+n))
(HERE/'r1-to-r2.patch').write_bytes(''.join(patch).encode())
a={r['name']:r['sha256'] for r in json.loads((R1/'function-manifest.json').read_text())['functions']}
c={r['name']:r['sha256'] for r in json.loads((HERE/'function-manifest.json').read_text())['functions']}
changed=sorted(k for k in a if k in c and a[k]!=c[k]);added=sorted(c.keys()-a.keys())
assert changed==['samurai_pd5v_acquire','samurai_pd5v_create','samurai_pd5v_destroy','samurai_pd5v_quiesce','samurai_pd5v_release']
assert added==['pd5v_unpublish_if_retired']
same=sorted(k for k in a if k in c and a[k]==c[k])
parent_files=['qcom_pmic_typec.c','qcom_pmic_typec.h','Makefile']
assert all(sha(HERE/n)==sha(R1/n) for n in parent_files)
dump('unchanged-functions.json',dict(changed_actual_functions=changed,new_actual_functions=added,
 byte_identical_actual_functions=same,byte_identical_parent_files={n:sha(HERE/n) for n in parent_files},
 original_7_groups_rerun=False,original_test_receipt_sha256=sha(R1/'test-result.json')))
dump('result.json',dict(frozen=True,context_lifetime_fix_implemented=True,default_enabled=False,
 source_sha256=sha(HERE/'qcom_pmic_typec_5v.c'),header_sha256=sha(HERE/'qcom_pmic_typec_5v.h'),
 narrow_patch_sha256=sha(HERE/'r1-to-r2.patch'),full_patch_sha256=sha(HERE/'pd5v-owner.patch'),
 test_passed=True,affected_test_groups=8,test_receipt_sha256=sha(HERE/'test-result.json'),
 object_build_passed=True,build_receipt_sha256=sha(HERE/'build-result.json'),objects=b['objects'],
 original_candidate_unchanged=True,original_7_groups_rerun=False,
 independent_review_pending=True,automatic_consumer=False,integration_or_hardware_approval=False,
 Image_or_module_linked=False,installed=False,phone_accessed=False,SSH_invoked=False,USB_invoked=False,SDK_invoked=False,Git_invoked=False,shared_source_or_config_modified=False))
files={p.name:dict(bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(HERE.iterdir()) if p.is_file() and p.name!='delivery.json'}
dump('delivery.json',dict(schema='samurai-pd5v-context-r2-delivery-v1',frozen=True,files=files,
 r1_delivery_sha256=sha(R1/'delivery.json'),execution_allowed=False,independent_review_pending=True))
print(json.dumps({n:sha(HERE/n) for n in ['qcom_pmic_typec_5v.c','qcom_pmic_typec_5v.h','r1-to-r2.patch','pd5v-owner.patch','test-result.json','build-result.json','result.json','delivery.json']},indent=2))
