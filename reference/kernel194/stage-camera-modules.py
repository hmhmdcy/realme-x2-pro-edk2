from pathlib import Path
import hashlib,json,host
ref=Path(__file__).resolve().parent;records=json.loads((ref/'imx471-modules-build-validation.json').read_text())['modules'];pmic=json.loads((ref/'pmic-module-build-validation.json').read_text())
items=[(Path(r['path']).name,r['sha256']) for r in records]+[('qcom-pm8008.ko',pmic['module_sha256'])]
assert all(hashlib.sha256((host.PRIVATE/n).read_bytes()).hexdigest()==h for n,h in items)
host.ssh('python3 -',input=b'''from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k194-baseline/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='512'
assert all(not Path('/sys/module/'+n).exists() for n in ['qcom_pm8008','v4l2_cci','imx471'])
Path('/var/lib/samurai/k194-modules').mkdir(mode=0o700)
''',timeout=20)
for n,h in items:host.upload(host.PRIVATE/n,'/var/lib/samurai/k194-modules/'+n)
for n in ['imx471-modules-build-validation.json','pmic-module-build-validation.json']:host.upload(ref/n,'/var/lib/samurai/k194-modules/'+n)
print('Three verified modules staged privately; installed modules unchanged')
