"""Bind reviewed offline candidate, affected test and private module receipts."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
t=json.loads((HERE/'test-result.json').read_text());b=json.loads((HERE/'build-result.json').read_text())
assert t['passed'] and b['passed'] and t['group_count']==10 and t['actual_functions']==17
assert b['test_receipt_sha256']==sha(HERE/'test-result.json')
for name,digest in t['files'].items():assert sha(HERE/name)==digest,name
for name,digest in b['files'].items():assert sha(HERE/name)==digest,name
names=['README.md','DESIGN.md','baseline.json','baseline-samurai-usb-input.c','samurai-usb-input.c',
 'samurai-usb-input-decode.h','usbin-init-core.h','provider-init.patch','generate-candidate.py','prepare-tests.py',
 'test-provider.c','tested-functions.inc','tested-struct.inc','function-manifest.json','run-tests.py',
 'test-result.json','build-private.py','build-result.json','freeze.py']
r=dict(passed=True,scope='offline default-disabled R7 minimal USBIN bit7 initialization candidate',
 files={name:sha(HERE/name) for name in names},module_sha256=b['module_sha256'],module_private=b['module'],
 default_enabled=False,hardware_validated=False,installed=False,hot_replacement_allowed=False,
 new_actual_function_groups=10,new_actual_provider_functions=17,poll_ms=1000,core_unchanged=True,decoder_unchanged=True,
 source_budget_unchanged=True,native_ref_proof_required=True,
 hardware_gate='temporary helper physical result and explicit future integration review before any adoption',
 phone_accessed=False,ssh_executed=False,usb_accessed=False,sdk_invoked=False,image_built=False,shared_tree_modified=False)
(HERE/'result.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(dict(passed=True,result_sha256=sha(HERE/'result.json'),driver_sha256=sha(HERE/'samurai-usb-input.c'),
 patch_sha256=sha(HERE/'provider-init.patch'),test_sha256=sha(HERE/'test-result.json'),build_sha256=sha(HERE/'build-result.json'),module_sha256=b['module_sha256']),indent=2))
