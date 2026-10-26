from pathlib import Path
import hashlib,json,os,shutil,subprocess,time

os.umask(0o077)
here=Path(__file__).resolve().parent
private=Path('/mnt/e/edk2-samurai-out/kernel218')
root=Path('/home/cy122/x2pro-linux/libcamera214-root')
log=private/'candidate-build-private.log'
assert not log.exists()
shutil.copyfile(here/'native_quad_bayer.h',root/'private/native_quad_bayer.h')
shutil.copyfile(here/'native-quad-test.cpp',root/'private/native-quad-test218.cpp')

def run(command,output,timeout):
    process=subprocess.Popen(command,stdout=output,stderr=subprocess.STDOUT)
    (private/'active-build-private.json').write_text(json.dumps(dict(pid=process.pid,command=command,started=time.time()),indent=2)+'\n')
    try:code=process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.terminate()
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:process.kill();process.wait()
        raise
    assert code==0, 'Build failed; inspect the existing log'

with log.open('wb') as output:
    run(['chroot',str(root),'/usr/bin/g++','-std=c++17','-O3','-Wall','-Wextra','-Werror','-pthread','-static','/private/native-quad-test218.cpp','-o','/private/native-quad-test218'],output,120)
    shutil.copyfile(root/'private/native-quad-test218',private/'native-quad-test218')
    run(['chroot',str(root),'/usr/bin/meson','setup','/work/libcamera218/output',
         '/work/libcamera218','--buildtype=debugoptimized','-Dwerror=true','-Dtest=true',
         '-Dpipelines=simple,virtual','-Dipas=simple','-Dsoftisp-gpu=enabled',
         '-Dcam=enabled','-Dqcam=disabled','-Dpycamera=disabled','-Dgstreamer=disabled',
         '-Dv4l2=disabled','-Ddocumentation=disabled','-Dipa-priv-key=/private/ipa214.rsa.pem'],output,180)
    run(['chroot',str(root),'/usr/bin/ninja','-C','/work/libcamera218/output','-j4'],output,3600)
report=dict(stage=218,candidate_simple_virtual_cpu_egl_build_passed=True,compiler_warnings_as_errors=True,
            all_upstream_tests_built=True,production_full_feature_packages_unchanged=True,
            static_arm_probe_sha256=hashlib.sha256((private/'native-quad-test218').read_bytes()).hexdigest(),
            static_arm_probe_bytes=(private/'native-quad-test218').stat().st_size,
            existing_ipa_signing_key_reused=True,no_package_device_install=True)
(here/'candidate-build-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
