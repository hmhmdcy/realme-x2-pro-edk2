from pathlib import Path
import host,json
ref=Path(__file__).resolve().parent;build=json.loads((ref/'front-helper-build-validation.json').read_text());test=json.loads((ref/'front-sequence-host-validation.json').read_text());assert test['source_sha256']==build['helper_source_sha256'] and test['asan_ubsan_passed']
code=b'''from pathlib import Path
import json,subprocess
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k193-baseline/boot-id-private.txt').read_bytes()
first=json.loads(Path('/var/lib/samurai/k193-front-identify/summary.json').read_text());assert first['gpio_directions_and_levels_restored'] and first['pmic_entire_sample_restored'] and first['module_parameters']==dict(sensor_id=0,restore_result=0,ready_samples=0,sequence_result=-524)
assert Path('/sys/module/samurai_front_identify').is_dir()
p=subprocess.run(['rmmod','samurai_front_identify'],capture_output=True,timeout=10);assert p.returncode==0 and not Path('/sys/module/samurai_front_identify').exists()
Path('/var/lib/samurai/k193-tools-r2').mkdir(mode=0o700)
'''
host.ssh('python3 -',input=code,timeout=20)
for p in [host.PRIVATE/'samurai-front-identify-k193r2-private.ko',ref/'front-helper-build-validation.json',ref/'samurai-front-identify.c']:
 host.upload(p,'/var/lib/samurai/k193-tools-r2/'+p.name)
data=(ref/'identify-front-once.py').read_text().replace("root/'k193-front-identify'","root/'k193-front-identify-r2'").replace('k193-tools/','k193-tools-r2/').replace("root/'k193-tools/samurai-front-identify-k193-private.ko'","root/'k193-tools-r2/samurai-front-identify-k193r2-private.ko'").replace('samurai-front-identify-k193-private.ko','samurai-front-identify-k193r2-private.ko')
(ref/'identify-front-once-r2.py').write_text(data)
print('Original completed failed attempt preserved; r2 staged, not loaded')
