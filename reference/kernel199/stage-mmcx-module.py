from pathlib import Path
import hashlib,json,host
ref=Path(__file__).resolve().parent;r=json.loads((ref/'mmcx-module-build-validation.json').read_text());p=host.PRIVATE/'qcom-camss-mmcx.ko';assert hashlib.sha256(p.read_bytes()).hexdigest()==r['module_sha256'];host.upload(p,'/var/lib/samurai/k199-modules/qcom-camss-mmcx.ko');host.upload(ref/'mmcx-module-build-validation.json','/var/lib/samurai/k199-modules/mmcx-module-build-validation.json');print('Integrated CAMSS module staged')
