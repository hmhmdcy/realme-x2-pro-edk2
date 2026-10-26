from pathlib import Path
import hashlib,json,host
ref=Path(__file__).resolve().parent;r=json.loads((ref/'pmic-module-build-validation.json').read_text());p=host.PRIVATE/'qcom-pm8008.ko';assert hashlib.sha256(p.read_bytes()).hexdigest()==r['module_sha256']
host.ssh('python3 -',input=b'''from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k195-baseline/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='512'
assert all(not Path('/sys/module/'+n).exists() for n in ['qcom_pm8008','qcom_pm8008_regulator','samurai_pmic_fixture'])
Path('/var/lib/samurai/k195-modules').mkdir(mode=0o700)
''',timeout=20)
for p in [p,ref/'pmic-module-build-validation.json']:host.upload(p,'/var/lib/samurai/k195-modules/'+p.name)
print('Recovery module staged; persistent installation unchanged')
