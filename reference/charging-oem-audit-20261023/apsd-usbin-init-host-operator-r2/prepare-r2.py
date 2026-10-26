"""Copy only the frozen OEM R2 artifact and provenance; no build or transport."""
from pathlib import Path
import hashlib,json
here=Path(__file__).resolve().parent
author=here.parent/'apsd-usbin-init-operator-window-r2'
old=here.parent/'apsd-usbin-init-host-candidate'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(author/'delivery.json')=='d3092c1b25348bb310e956ef6a76e4903b3c051be376c8823fa4beb0458ff4b3'
d=json.loads((author/'delivery.json').read_text())
for name,digest in d['files'].items():assert sha(author/name)==digest,name
module=Path(d['module_export_path']);assert sha(module)==d['module_sha256']=='2edcafa86335a2c01be52058c3432c82241460b692e1c638e08f7ce071098f78'
for src,dst in [(module,'samurai-usbin-init.ko'),(author/'protocol.json','helper-protocol.json'),(author/'actual-state-fixtures.json','actual-state-fixtures.json')]:
    assert not(here/dst).exists();(here/dst).write_bytes(src.read_bytes())
pins=json.loads((old/'input-pins.json').read_text())
paths={'helper_delivery':author/'delivery.json','helper_protocol':author/'protocol.json','helper_build':author/'build-result.json',
       'helper_core':author/'usbin-init-core.h','helper_fixtures':author/'actual-state-fixtures.json','helper_test':author/'test-result.json'}
for name,p in paths.items():pins[name]={'path':str(p),'sha256':sha(p)}
(here/'input-pins.json').write_text(json.dumps(pins,indent=2)+'\n')
print(json.dumps({'prepared':True,'module_sha256':sha(here/'samurai-usbin-init.ko'),'no_build_or_transport':True}))
