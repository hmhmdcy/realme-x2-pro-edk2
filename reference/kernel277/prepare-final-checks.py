"""Prepare checks tied to the actual 276 boot and 277 userspace transaction."""
from pathlib import Path
R=Path(__file__).resolve().parent
s=(R.parent/'kernel276/final-health.py').read_text()
for a,b in [("(R/'test-manager-lifetime.py')","(R.parent/'kernel276/test-manager-lifetime.py')"),
 ("'k276-final-health'","'k277-final-health'"),('k275-main-transaction/new-manifest-private.json','k277-package-transaction/new-manifest-private.json'),
 ('k276-cci-transaction-r2/module-inventory-before-private.json','k277-package-transaction/module-inventory-before-private.json'),
 ('k276-services-current-private.json','k277-services-verified-private.json'),('stage=276','stage=277'),('other775_modules_unchanged=True','all776_modules_unchanged=True')]:
 assert a in s,a;s=s.replace(a,b)
a="assert len(now)==776 and set(now)==set(old) and changed==['kernel/drivers/i2c/busses/i2c-qcom-cci.ko'] and now[changed[0]]=='b2808f63c0e290a7aa5808de687d2001b8f936595a8632d2a1055b05aa8ca42b'"
assert a in s;s=s.replace(a,'assert len(now)==776 and set(now)==set(old) and changed==[]')
s=s.replace('print(json.dumps(d,indent=2))',"print(json.dumps({k:v for k,v in d.items() if k not in ['modules','camera_idle_health']},indent=2))")
compile(s,'final-health.py','exec');(R/'final-health.py').write_text(s)
s=(R.parent/'kernel276/inspect-services.py').read_text().replace('stage=276','stage=277').replace('k276-services-current-private.json','k277-services-verified-private.json')
compile(s,'inspect-services.py','exec');(R/'inspect-services.py').write_text(s)
s=(R.parent/'kernel276/regress-four-cameras.py').read_text().replace("assert json.loads((R/'main-capture-validation.json').read_text())['all_passed']","assert json.loads((R/'focus-metadata-r1-validation.json').read_text())['error'] is None")
s=s.replace(".replace('k273','k276').replace('stage=273','stage=276')",".replace('k273','k277').replace('k277-work','k276-work').replace('stage=273','stage=277')")
compile(s,'regress-four-cameras.py','exec');(R/'regress-four-cameras.py').write_text(s)
print('Services, four-camera regression and current payload/module checks prepared')
