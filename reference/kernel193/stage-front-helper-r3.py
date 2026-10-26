from pathlib import Path
import host,json
ref=Path(__file__).resolve().parent;build=json.loads((ref/'front-helper-build-validation.json').read_text());test=json.loads((ref/'front-sequence-host-validation.json').read_text());assert test['source_sha256']==build['helper_source_sha256'] and test['asan_ubsan_passed'] and test['clock_requires_live_power_domain']
code=b'''from pathlib import Path
import json,subprocess
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k193-baseline/boot-id-private.txt').read_bytes()
prior=json.loads(Path('/var/lib/samurai/k193-front-identify-r2/summary.json').read_text());assert prior['gpio_directions_and_levels_restored'] and prior['pmic_entire_sample_restored'] and prior['module_parameters']==dict(sensor_id=0,restore_result=0,ready_samples=2,sequence_result=-16)
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='512'
log=subprocess.check_output(['dmesg']);assert log.count(b'WARNING:')==1 and b"cam_cc_mclk2_clk status stuck at 'off'" in log and b'Oops:' not in log
p=subprocess.run(['rmmod','samurai_front_identify'],capture_output=True,timeout=10);assert p.returncode==0 and not Path('/sys/module/samurai_front_identify').exists()
Path('/var/lib/samurai/k193-tools-r3').mkdir(mode=0o700)
'''
host.ssh('python3 -',input=code,timeout=20)
for p in [host.PRIVATE/'samurai-front-identify-k193r3-private.ko',ref/'front-helper-build-validation.json',ref/'samurai-front-identify.c']:
 host.upload(p,'/var/lib/samurai/k193-tools-r3/'+p.name)
data=(ref/'identify-front-once-r2.py').read_text().replace('k193-front-identify-r2','k193-front-identify-r3').replace('k193-tools-r2','k193-tools-r3').replace('samurai-front-identify-k193r2-private.ko','samurai-front-identify-k193r3-private.ko')
data=data.replace("read_text().strip()=='0'","read_text().strip()=='512'").replace("report['taint']==0","report['taint']==512")
data+="\nassert values.get('sequence_result')==0 and values.get('sensor_id')==0x471 and values.get('ready_samples')==2\n"
(ref/'identify-front-once-r3.py').write_text(data)
print('PM-domain reference fix staged; prior clock warning and failed attempt retained')
