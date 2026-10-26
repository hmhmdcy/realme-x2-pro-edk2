from pathlib import Path
import host,json,hashlib
ref=Path(__file__).resolve().parent;out=host.PRIVATE
module=out/'samurai-vio-phandle.ko';meta=json.loads((ref/'vio-helper-build-validation.json').read_text());assert hashlib.sha256(module.read_bytes()).hexdigest()==meta['module_sha256']
p=host.ssh('python3 -',input=b'''from pathlib import Path
import json
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k200-runtime/boot-id-private.txt').read_bytes()
assert all(not Path('/sys/module/'+n).exists() for n in ['i2c_qcom_cci','samurai_cci_bringup','samurai_vio_phandle','qcom_pm8008','v4l2_cci'])
print(Path('/var/lib/samurai/k200-modules/manifest.json').read_text())
''')
manifest=json.loads(p.stdout)
for row in manifest:
 if row['file']=='samurai-vio-phandle.ko':
  assert row['sha256']=='9e83668ed052ce24d8f1a5b76a924cebe3ce33cdef17b38fc870755c57dbe230';row['sha256']=meta['module_sha256']
(ref/'live-module-manifest-r2.json').write_text(json.dumps(manifest,indent=2)+'\n')
host.upload(module,'/var/lib/samurai/k200-modules/samurai-vio-phandle.ko');host.upload(ref/'live-module-manifest-r2.json','/var/lib/samurai/k200-modules/manifest.json')
for name in ['prepare-physical-live-native.py','build-live-overlay.py','capture-front-mmcx-repeat.py']:
 p=ref/name;p.write_text(p.read_text().replace('k200-live-prepare-r1','k200-live-prepare-r2'))
print('K200_REVISED_READ_ONLY_VIO_HELPER_STAGED_R1_FAILURE_PRESERVED')
