from pathlib import Path
import hashlib,json,host
ref=Path(__file__).resolve().parent;r=json.loads((ref/'pmic-fixture-build-validation.json').read_text());p=host.PRIVATE/'samurai-pmic-fixture.ko';assert hashlib.sha256(p.read_bytes()).hexdigest()==r['module_sha256']
host.ssh('python3 -',input=b'''from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k194-baseline/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='512'
assert all(not Path('/sys/module/'+n).exists() for n in ['samurai_pmic_fixture','qcom_pm8008','qcom_pm8008_regulator'])
assert not Path('/var/lib/samurai/k194-pmic-coldprobe').exists()
''',timeout=20)
for p in [p,ref/'pmic-fixture-build-validation.json',ref/'probe-q-reset-address.py']:host.upload(p,'/var/lib/samurai/k194-modules/'+p.name)
print('Verified reversible fixture staged; no live device node added yet')
