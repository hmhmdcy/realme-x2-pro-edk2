from pathlib import Path
import hashlib,json,host
ref=Path(__file__).resolve().parent;meta=json.loads((ref/'imx471-module-build-validation.json').read_text());module=host.PRIVATE/'imx471.ko';assert hashlib.sha256(module.read_bytes()).hexdigest()==meta['module_sha256']
host.ssh('python3 -',input=b'''from pathlib import Path
import shutil
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k196-baseline/boot-id-private.txt').read_bytes()
assert all(not Path('/sys/module/'+n).exists() for n in ['samurai_front_overlay','imx471','samurai_vio_phandle','samurai_cci_bringup','qcom_pm8008'])
stage=root/'k196-modules';shutil.copyfile(stage/'manifest.json',root/'k196-front-probe-r3/loaded-manifest.json')
assert not (stage/'imx471-before-required-clock-retained.ko').exists();shutil.copyfile(stage/'imx471.ko',stage/'imx471-before-required-clock-retained.ko')
''',timeout=20)
records=json.loads((ref/'live-module-manifest.json').read_text())
for r in records:
 if r['file']=='imx471.ko':r['sha256']=meta['module_sha256']
(ref/'live-module-manifest.json').write_text(json.dumps(records,indent=2)+'\n');host.upload(module,'/var/lib/samurai/k196-modules/imx471.ko');host.upload(ref/'live-module-manifest.json','/var/lib/samurai/k196-modules/manifest.json');print('Required-clock sensor module staged; former module preserved')
