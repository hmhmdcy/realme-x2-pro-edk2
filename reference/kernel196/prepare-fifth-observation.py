from pathlib import Path
import hashlib,json,host,shutil
p=Path(__file__).resolve().parent
for source,dest in [('prepare-live-native-r4.py','prepare-live-native-r5.py'),('build-live-overlay-r4.py','build-live-overlay-r5.py'),('probe-front-driver-r4.py','probe-front-driver-r5.py')]:
 s=(p/source).read_text().replace('k196-live-prepare-r4','k196-live-prepare-r5').replace('live-input-r4-private','live-input-r5-private').replace('k196-front-probe-r4','k196-front-probe-r5').replace('sensor_probe_only_no_camss_remote_endpoint=True','real_csiphy2_remote_endpoint_present=True')
 (p/dest).write_text(s)
module=host.PRIVATE/'imx471.ko';meta=json.loads((p/'imx471-module-build-validation.json').read_text());assert hashlib.sha256(module.read_bytes()).hexdigest()==meta['module_sha256']
host.ssh('python3 -',input=b'''from pathlib import Path
import shutil
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k196-baseline/boot-id-private.txt').read_bytes()
assert all(not Path('/sys/module/'+n).exists() for n in ['samurai_front_overlay','imx471','samurai_vio_phandle','samurai_cci_bringup','qcom_pm8008'])
stage=root/'k196-modules';shutil.copyfile(stage/'manifest.json',root/'k196-front-probe-r4/loaded-manifest.json')
assert not (stage/'imx471-required-clock-native-retained.ko').exists();shutil.copyfile(stage/'imx471.ko',stage/'imx471-required-clock-native-retained.ko');shutil.copyfile(stage/'front.dtbo',stage/'front-no-media-remote-retained.dtbo')
''',timeout=20)
records=json.loads((p/'live-module-manifest.json').read_text())
for r in records:
 if r['file']=='imx471.ko':r['sha256']=meta['module_sha256']
(p/'live-module-manifest.json').write_text(json.dumps(records,indent=2)+'\n');host.upload(module,'/var/lib/samurai/k196-modules/imx471.ko');host.upload(p/'live-module-manifest.json','/var/lib/samurai/k196-modules/manifest.json');print('Original V4L2 clock path restored; fifth attempt connects the actual CAMSS endpoint')
