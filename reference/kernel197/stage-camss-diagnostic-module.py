from pathlib import Path
import hashlib,json,host
ref=Path(__file__).resolve().parent;out=host.PRIVATE;r=json.loads((ref/'camss-diagnostic-module-build-validation.json').read_text());assert hashlib.sha256((out/'qcom-camss-diagnostic.ko').read_bytes()).hexdigest()==r['module_sha256'];host.upload(out/'qcom-camss-diagnostic.ko','/var/lib/samurai/k197-modules/qcom-camss.ko');host.upload(ref/'camss-diagnostic-module-build-validation.json','/var/lib/samurai/k197-modules/camss-diagnostic-module-build-validation.json');print('CAMSS candidate staged; persistent module file untouched')
