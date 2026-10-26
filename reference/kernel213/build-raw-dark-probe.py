from pathlib import Path
import host,json,sys
here=Path(__file__).resolve().parent;retry=sys.argv[1:]==['--r2'];assert not sys.argv[1:] or retry
host.upload(here/'raw-dark-probe.cpp','/var/lib/samurai/k213-libcamera-build/raw-dark-probe.cpp')
code=r'''
from pathlib import Path
import hashlib,json,os,shlex,subprocess
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k213-baseline/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
out=root/'k213-libcamera-build';sdk=root/'k213-libcamera-sdk';prefix=Path('/run/samurai-camera213-helper');env=json.loads((out/'build-environment-private.json').read_text())
target=out/'raw-dark-probe';assert not target.exists()
args=shlex.split(env['CXX'])+['-std=c++20','-O2','-Wall','-Wextra','-pthread','-I'+str(prefix/'usr/include/libcamera'),str(out/'raw-dark-probe.cpp'),'-L'+str(prefix/'usr/lib'),'-Wl,-rpath-link,'+str(sdk/'usr/lib'),'-Wl,-rpath,'+str(prefix/'usr/lib'),'-lcamera','-lcamera-base','-o',str(target)]
with (out/'compile-raw-dark-probe-private.log').open('wb') as log:subprocess.run(args,env=env,check=True,stdout=log,stderr=subprocess.STDOUT,timeout=120)
public=Path('/run/samurai-camera213-raw-dark-probe');assert not public.exists();public.write_bytes(target.read_bytes());public.chmod(0o755)
report=dict(stage=213,raw10_dark_statistics_probe_built=True,uses_real_camera_sensor_camss_and_cpu_isp=True,restores_test_pattern_on_exit=True,excludes_six_padding_bytes_per_raw_row=True,six_frames_maximum=True,no_external_illumination=True,no_product_replacement=True,binary_sha256=hashlib.sha256(target.read_bytes()).hexdigest())
(out/'raw-dark-probe-build-summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
if retry:code=code.replace('compile-raw-dark-probe-private.log','compile-raw-dark-probe-r2-private.log')
p=host.ssh('python3 -',input=code.encode(),timeout=180);(host.PRIVATE/'raw-dark-probe-build-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);(here/'raw-dark-probe-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
