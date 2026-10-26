from pathlib import Path
import host,json,hashlib
here=Path(__file__).resolve().parent
patch=here.parent.parent/'linux-port/camera/libcamera/0009-softisp-cpu-initialize-luts.patch'
assert hashlib.sha256(patch.read_bytes()).hexdigest()=='852334274b074608d72a00380f187d2b6a5a852bfdc3e023905aff87bf3dd0ca'
host.upload(patch,'/var/lib/samurai/k213-libcamera-build/0009-softisp-cpu-initialize-luts.patch')
code=r'''
from pathlib import Path
import hashlib,json,os,subprocess,time
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k213-baseline/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
out=root/'k213-libcamera-build';sdk=root/'k213-libcamera-sdk';build=out/'build';source=out/'source/libcamera-v0.7.2'
assert json.loads((out/'helper-candidate-summary.json').read_text())['installed_camera_products_unchanged']
target=source/'src/libcamera/software_isp/debayer_cpu.cpp';header=target.with_suffix('.h')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(target)=='4e83f9c1ec052074fe33ceb8b3847838506b42ea83c504782c4a3a5943b40bc2'
assert sha(header)=='0b137badef443b0f1db8c715002fcb8fb6f1602e3ec35915b8fa76a1bfa287f8'
assert sha(out/'0009-softisp-cpu-initialize-luts.patch')=='852334274b074608d72a00380f187d2b6a5a852bfdc3e023905aff87bf3dd0ca'
assert sha(source/'src/ipa/libipa/camera_sensor_helper.cpp')=='f313c423097ead6345db614706a075165dc775f5e08c65b4823cb6bac3271b90'
assert sha(source/'src/libcamera/sensor/camera_sensor_properties.cpp')=='938ea102ca456b3d853d7bffc18822a2c674dfd76d4c65c4e3c282e13d618b14'
backup=out/'debayer_cpu-helper-before-lut-private.cpp';assert not backup.exists();backup.write_bytes(target.read_bytes())
text=target.read_text();assert text.count('\tparams_.gamma = 1.0;')==1;target.write_text(text.replace('\tparams_.gamma = 1.0;','\tparams_.gamma = -1.0;'))
assert sha(target)=='febace312318e7070bc052ebee20aab9628911b875807aae979f33a27712a4ba'
original=json.loads((root/'k213-baseline/products-before-private.json').read_text());db=Path('/lib/apk/db/installed').read_bytes()
assert all(sha(Path(name))==digest for name,digest in original.items())
env=json.loads((out/'build-environment-private.json').read_text());logpath=out/'compile-lut-private.log';assert not logpath.exists()
with logpath.open('wb') as log:
    process=subprocess.Popen([str(sdk/'usr/bin/ninja'),'-C',str(build),'-j2'],env=env,stdout=log,stderr=subprocess.STDOUT)
    (out/'active-build-private.json').write_text(json.dumps(dict(phase='compile-lut',pid=process.pid,started_monotonic=time.monotonic()),indent=2)+'\n')
    result=process.wait(timeout=600)
assert result==0 and db==Path('/lib/apk/db/installed').read_bytes() and all(sha(Path(name))==digest for name,digest in original.items())
assert sha(header)=='0b137badef443b0f1db8c715002fcb8fb6f1602e3ec35915b8fa76a1bfa287f8'
report=dict(stage=213,lut_candidate_compiled=True,single_line_gamma_sentinel_fix=True,header_and_public_abi_unchanged=True,helper_properties_identical_to_candidate_a=True,helper_candidate_a_staging_preserved=True,gpu_isp_support_retained=True,native_two_compile_jobs=True,package_database_unchanged=True,installed_camera_products_unchanged=True,debayer_cpu_source_sha256=sha(target))
(out/'lut-build-summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=700);(host.PRIVATE/'lut-build-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);(here/'lut-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
