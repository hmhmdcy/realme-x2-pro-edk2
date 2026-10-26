from pathlib import Path
import hashlib,json,host
ref=Path(__file__).resolve().parent;r=json.loads((ref/'vio-helper-build-validation.json').read_text());p=host.PRIVATE/'samurai-vio-phandle.ko';assert hashlib.sha256(p.read_bytes()).hexdigest()==r['module_sha256']
host.ssh('python3 -',input=b'''from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k195-baseline/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='512'
assert not Path('/sys/module/samurai_vio_phandle').exists() and not Path('/var/lib/samurai/k195-vio-lookup').exists()
assert not Path('/sys/firmware/devicetree/base/soc@0/rsc@18200000/regulators-1/ldo1/phandle').exists()
''',timeout=20)
for p in [p,ref/'vio-helper-build-validation.json']:host.upload(p,'/var/lib/samurai/k195-modules/'+p.name)
print('VIO lookup-only helper staged; no live tree changes yet')
