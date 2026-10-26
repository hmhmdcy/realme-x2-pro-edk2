from pathlib import Path
import hashlib,json,host,shutil
ref=Path(__file__).resolve().parent;out=host.PRIVATE;records=[]
for stage,file,meta,key in [(193,'samurai-cci-bringup-k193-private.ko','cci-helper-build-validation.json','candidate_sha256'),(195,'qcom-pm8008.ko','pmic-module-build-validation.json','module_sha256'),(195,'samurai-vio-phandle.ko','vio-helper-build-validation.json','module_sha256'),(196,'imx471.ko','imx471-module-build-validation.json','module_sha256'),(196,'v4l2-cci.ko','imx471-module-build-validation.json','cci_module_sha256'),(196,'samurai-front-overlay.ko','overlay-helper-build-validation.json','module_sha256')]:
 metadata=json.loads((ref.parent/('kernel'+str(stage))/meta).read_text());p=out.parent/('kernel'+str(stage))/file;assert hashlib.sha256(p.read_bytes()).hexdigest()==metadata[key];records.append(dict(file=file,sha256=metadata[key],path=p))
host.ssh('python3 -',input=b'''from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k198-baseline/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='512'
assert all(not Path('/sys/module/'+n).exists() for n in ['samurai_cci_bringup','samurai_vio_phandle','samurai_front_overlay','qcom_pm8008','imx471','v4l2_cci'])
assert Path('/var/lib/samurai/k198-modules').is_dir() and not Path('/var/lib/samurai/k198-modules/manifest.json').exists()
''',timeout=20)
for r in records:host.upload(r['path'],'/var/lib/samurai/k198-modules/'+r['file'])
manifest=[{k:v for k,v in r.items() if k!='path'} for r in records];(ref/'live-module-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');host.upload(ref/'live-module-manifest.json','/var/lib/samurai/k198-modules/manifest.json');print('Six verified modules staged; persistent module tree unchanged')
