"""Receipt-only freeze, never runs tests/builds or changes a frozen input."""
from pathlib import Path
import hashlib,json
H=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
t=json.loads((H/'test-result.json').read_bytes());b=json.loads((H/'build-result.json').read_bytes());s=json.loads((H/'scope-result.json').read_bytes())
assert t['passed'] and t['affected_groups']==9 and b['passed'] and s['passed']
for n,v in t['tested_files'].items():assert sha(H/n)==v,n
for n,v in b['sources'].items():assert sha(H/n)==v,n
assert b['test_receipt_sha256']==sha(H/'test-result.json')
assert b['shared_unchanged'] and b['shared_final_unchanged']
assert s['patch_sha256']==sha(H/'lifetime.patch')
assert b['Image_or_module_linked'] is False
for n,v in json.loads((H/'history/build-01-include-order-failed.json').read_bytes())['sources'].items():assert sha(H/'history/01-source'/n)==v
names=sorted(p.name for p in H.iterdir() if p.is_file() and p.name!='delivery.json')
r=dict(passed=True,scope='offline actual femto/DWC owner PHY provider devres/PM lifecycle only; not deployed or a route/APSD grant',
 files={n:sha(H/n) for n in names},
 history={str(p.relative_to(H)).replace('\\','/'):sha(p) for p in sorted((H/'history').rglob('*')) if p.is_file()},
 component_bases=json.loads((H/'source-inputs.json').read_bytes()),
 new_actual_groups=9,old_phy_8_and_pd_bridge_14_reused_not_rerun=True,
 private_build=dict(exec_session=90767,exit_code=0,objects=b['objects'],shared_unchanged=True,W1=True,Werror=True,zero_diagnostics=True),
 source_and_scope_bound=True,default_owner_optin_unchanged=True,final_EOPNOTSUPP=True,
 no_1341_authority=True,route_contract_missing=True,write_time_lease_fence_missing=True,
 kernel_lockdep_or_hardware_validated=False,phone_accessed=False,SDK_invoked=False,Git_invoked=False,
 private_test_binaries_not_delivery=True,private_kernel_objects_not_delivery=True)
(H/'delivery.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(dict(passed=True,delivery_sha256=sha(H/'delivery.json'),patch_sha256=sha(H/'lifetime.patch'),test_sha256=sha(H/'test-result.json'),build_sha256=sha(H/'build-result.json'))))
