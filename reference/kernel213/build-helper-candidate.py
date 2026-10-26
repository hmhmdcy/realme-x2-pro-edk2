from pathlib import Path
import hashlib,json,os,subprocess,time
os.umask(0o077);root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k213-baseline/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
out=root/'k213-libcamera-build';sdk=root/'k213-libcamera-sdk';source=out/'source/libcamera-v0.7.2';build=out/'build'
assert json.loads((out/'sdk-ready-private.json').read_text())['independent_sdk_ready'] and not build.exists()
assert hashlib.sha256((source/'src/ipa/libipa/camera_sensor_helper.cpp').read_bytes()).hexdigest()=='f313c423097ead6345db614706a075165dc775f5e08c65b4823cb6bac3271b90'
assert hashlib.sha256((source/'src/libcamera/sensor/camera_sensor_properties.cpp').read_bytes()).hexdigest()=='938ea102ca456b3d853d7bffc18822a2c674dfd76d4c65c4e3c282e13d618b14'
db=Path('/lib/apk/db/installed').read_bytes();env=json.loads((out/'build-environment-private.json').read_text())
args=[str(sdk/'usr/bin/meson'),'setup',str(build),str(source),'--prefix=/usr','--libdir=lib','--libexecdir=/usr/libexec','--sysconfdir=/etc','--buildtype=release','--wrap-mode=nodownload','-Dwerror=false','-Dpipelines=simple,uvcvideo,virtual','-Dipas=simple','-Dsoftisp-gpu=enabled','-Dcam=enabled','-Dcam-output-kms=disabled','-Dcam-output-sdl2=disabled','-Dcam-jpeg=auto','-Dapps-output-dng=disabled','-Ddocumentation=disabled','-Dgstreamer=disabled','-Dpycamera=disabled','-Dqcam=disabled','-Dlc-compliance=disabled','-Dtest=false','-Dtracing=disabled','-Dv4l2=enabled']
for phase,command in [('configure-helper',args),('compile-helper',[str(sdk/'usr/bin/ninja'),'-C',str(build),'-j2'])]:
    logpath=out/(phase+'-private.log');assert not logpath.exists()
    with logpath.open('wb') as log:
        process=subprocess.Popen(command,env=env,stdout=log,stderr=subprocess.STDOUT)
        (out/'active-build-private.json').write_text(json.dumps(dict(phase=phase,pid=process.pid,started_monotonic=time.monotonic()),indent=2)+'\n')
        result=process.wait(timeout=1200)
    assert result==0,phase
assert db==Path('/lib/apk/db/installed').read_bytes()
report=dict(stage=213,helper_properties_candidate_compiled=True,initial_lut_fix_not_yet_applied=True,compiled_pipelines=['simple','uvcvideo','virtual'],gpu_isp_support_retained=True,native_two_compile_jobs=True,package_database_unchanged=True,installed_camera_products_unchanged=True)
(out/'helper-build-summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
