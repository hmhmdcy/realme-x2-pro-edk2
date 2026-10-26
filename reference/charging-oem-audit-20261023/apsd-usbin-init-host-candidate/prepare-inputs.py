"""Pin reviewed local bytes and copy the already-built private helper; no build."""
from pathlib import Path
import hashlib
import json

HERE=Path(__file__).resolve().parent
REF=HERE.parents[1]
HELPER=HERE.parent/'apsd-usbin-init-candidate'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(HELPER/'delivery.json')=='2f5bfd92b493a9330a7a408523db47f31d9659c8b4bf39bea43a6f7030e5b492'
delivery=json.loads((HELPER/'delivery.json').read_text())
for name,digest in delivery['files'].items():assert sha(HELPER/name)==digest
ko=Path(delivery['module_path']);assert sha(ko)==delivery['module_sha256']
(HERE/'samurai-usbin-init.ko').write_bytes(ko.read_bytes())
(HERE/'helper-protocol.json').write_bytes((HELPER/'protocol.json').read_bytes())
paths={'r7_launcher':REF/'charging-ui-audit-20261023/icon-capture-r7-candidate/launcher.py',
    'r7_pins':REF/'charging-ui-audit-20261023/icon-capture-r7-candidate/identity-pins.json',
    'r8_handoff':REF/'charging-management-20261023/r8-handoff-result.json',
    'helper_delivery':HELPER/'delivery.json','helper_protocol':HELPER/'protocol.json'}
pins={name:{'path':str(p),'sha256':sha(p)} for name,p in paths.items()}
(HERE/'input-pins.json').write_text(json.dumps(pins,indent=2)+'\n')
print(json.dumps({'local_inputs_pinned':True,'module_sha256':sha(HERE/'samurai-usbin-init.ko'),'phone_accessed':False,'sdk_invoked':False}))
