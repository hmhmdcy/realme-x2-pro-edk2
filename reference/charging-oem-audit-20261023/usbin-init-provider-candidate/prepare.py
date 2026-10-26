"""Freeze R7 provider + unchanged FLOAT decoder and diagnostic init core."""
from pathlib import Path
import hashlib,json,re,shutil
HERE=Path(__file__).resolve().parent;PARENT=HERE.parent;REF=PARENT.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
driver=REF/'charging-management-20261023/samurai-usb-input.c'
decoder=PARENT/'source-float-candidate/samurai-usb-input-decode.h'
core=PARENT/'apsd-usbin-init-candidate/usbin-init-core.h'
assert sha(driver)=='b712764fbd4ab24475ae1ba030ee4c26c7eb048a6038488a5435b44ef7eb7098'
assert sha(decoder)=='a17caa2cbeb2352da249474e0265fa96745f544d96a29d0ebe8f14c656d548fd'
assert sha(core)=='80aa42747f211884e838bc7508f746efe1a0800194dd80de51956f2b55f11dd9'
build=json.loads((REF/'charging-management-20261023/source-float-build-result.json').read_text())
assert build['passed'] and build['module_sha256']=='7d4e0f948b993a6e0cc9459bac4ade2db2fe7b88ce7b7d462ea34bcb933c4f70'
assert build['sources']=={driver.name:sha(driver),decoder.name:sha(decoder)}
handoff=json.loads((REF/'charging-management-20261023/r8-handoff-result.json').read_text())
assert handoff['passed'] and handoff['release']=='7.3.0-rc6-rmx1931-samurai-k363+'
for origin,name in [(driver,'baseline-samurai-usb-input.c'),(decoder,decoder.name),(core,core.name)]:
 target=HERE/name
 if target.exists():assert target.read_bytes()==origin.read_bytes()
 else:shutil.copy2(origin,target)
assert 'msecs_to_jiffies(1000)' in driver.read_text()
r=dict(passed=True,stage='design/source baseline only',
 files={name:sha(HERE/name) for name in ['baseline-samurai-usb-input.c',decoder.name,core.name]},
 build_receipt_sha256=sha(REF/'charging-management-20261023/source-float-build-result.json'),
 module_sha256=build['module_sha256'],config_sha256=build['config_sha256'],modinfo=build['modinfo'],
 retained_runtime_receipt_sha256=sha(REF/'charging-management-20261023/r8-handoff-result.json'),
 runtime_usb_note_sha256=handoff['loaded_notes_sha256']['samurai-usb-input'],
 helper_delivery_sha256=sha(PARENT/'apsd-usbin-init-candidate/delivery.json'),
 OEM_scope_sha256=sha(PARENT/'apsd-lifecycle/start-on-cc-scope-r8/result.json'),
 actual_poll_ms=1000,source_budget_calculation_to_remain_byte_exact=True,default_opt_in=False,
 hardware_initialization_validated=False,phone_accessed=False,SDK_invoked=False,shared_writes=False)
(HERE/'baseline.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(passed=True,actual_poll_ms=1000)))
