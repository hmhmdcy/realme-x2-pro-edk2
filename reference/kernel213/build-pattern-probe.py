from pathlib import Path
import host,json,sys
here=Path(__file__).resolve().parent;retry=sys.argv[1:]==['--r2'];assert not sys.argv[1:] or retry
host.upload(here/'isp-pattern-probe.cpp','/var/lib/samurai/k213-libcamera-build/isp-pattern-probe.cpp')
code=r'''
from pathlib import Path
import hashlib,json,os,shlex,subprocess
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k213-baseline/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
out=root/'k213-libcamera-build';sdk=root/'k213-libcamera-sdk';prefix=Path('/run/samurai-camera213-helper');env=json.loads((out/'build-environment-private.json').read_text())
target=out/'isp-pattern-probe';assert not target.exists()
args=shlex.split(env['CXX'])+['-std=c++20','-O2','-Wall','-Wextra','-pthread','-I'+str(prefix/'usr/include/libcamera'),str(out/'isp-pattern-probe.cpp'),'-L'+str(prefix/'usr/lib'),'-Wl,-rpath-link,'+str(sdk/'usr/lib'),'-Wl,-rpath,'+str(prefix/'usr/lib'),'-lcamera','-lcamera-base','-o',str(target)]
with (out/'compile-pattern-probe-private.log').open('wb') as log:subprocess.run(args,env=env,check=True,stdout=log,stderr=subprocess.STDOUT,timeout=120)
public=Path('/run/samurai-camera213-pattern-probe');assert not public.exists();public.write_bytes(target.read_bytes());public.chmod(0o755)
report=dict(stage=213,ambient_independent_sensor_color_bar_probe_built=True,uses_real_camera_sensor_camss_and_cpu_isp=True,restores_test_pattern_on_exit=True,six_frames_maximum=True,no_external_illumination=True,no_product_replacement=True,binary_sha256=hashlib.sha256(target.read_bytes()).hexdigest())
(out/'pattern-probe-build-summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
if retry:code=code.replace('compile-pattern-probe-private.log','compile-pattern-probe-r2-private.log')
p=host.ssh('python3 -',input=code.encode(),timeout=180);(host.PRIVATE/'pattern-probe-build-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);(here/'pattern-probe-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
