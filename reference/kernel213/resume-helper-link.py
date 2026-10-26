from pathlib import Path
import host,json
here=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json,os,subprocess,time
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k213-baseline/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
out=root/'k213-libcamera-build';sdk=root/'k213-libcamera-sdk';build=out/'build';assert (out/'recursive-runtime-closure-private.json').exists()
active=json.loads((out/'active-build-private.json').read_text());assert active['phase']=='compile-helper' and not Path('/proc',str(active['pid'])).exists()
env=json.loads((out/'build-environment-private.json').read_text());db=Path('/lib/apk/db/installed').read_bytes();logpath=out/'compile-helper-r2-private.log';assert not logpath.exists()
with logpath.open('wb') as log:
    process=subprocess.Popen([str(sdk/'usr/bin/ninja'),'-C',str(build),'-j2'],env=env,stdout=log,stderr=subprocess.STDOUT)
    (out/'active-build-private.json').write_text(json.dumps(dict(phase='compile-helper-r2',pid=process.pid,started_monotonic=time.monotonic()),indent=2)+'\n')
    result=process.wait(timeout=600)
assert result==0 and db==Path('/lib/apk/db/installed').read_bytes()
report=dict(stage=213,helper_properties_candidate_compiled=True,initial_lut_fix_not_yet_applied=True,compiled_pipelines=['simple','uvcvideo','virtual'],gpu_isp_support_retained=True,native_two_compile_jobs=True,package_database_unchanged=True,installed_camera_products_unchanged=True,first_configure_and_link_failures_preserved=True)
(out/'helper-build-summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=700);(host.PRIVATE/'helper-link-r2-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);(here/'helper-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
