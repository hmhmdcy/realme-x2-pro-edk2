from pathlib import Path
import hashlib,json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
source=(HERE.parent/'kernel445/check-runtime-inputs.py').read_text().replace('stage=445','stage=446')
exec(compile(source,str(HERE/'check-runtime-inputs.py'),'exec'))
installed=json.loads((HERE.parent/'kernel440/current-state-validation.json').read_text())
profiles={}
for model in ['imx319','s5k3m5','imx471']:
 p=P.parent/'kernel440'/('factory-'+model+'-private.yaml');assert p.is_file()
 digest=hashlib.sha256(p.read_bytes()).hexdigest();assert digest==installed['private_profiles'][model]
 profiles[model]=dict(path=str(p),sha256=digest)
(P/'extra-profiles-private.json').write_text(json.dumps(profiles,indent=2)+'\n')
r=json.loads((HERE/'runtime-inputs-validation.json').read_text());r.update(other_three_formal440_stock_profiles_reused=True)
(HERE/'runtime-inputs-validation.json').write_text(json.dumps(r,indent=2)+'\n')
