from pathlib import Path
import hashlib,json,shutil,subprocess

here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel225');sdk=Path('/home/cy122/x2pro-linux/libcamera214-root')
assert json.loads((here/'package-build-validation.json').read_text())['framework_and_config_packages_built']
source=sdk/'private/agc-control-regression225.cpp';assert not source.exists();shutil.copyfile(here/'agc-control-regression.cpp',source)
b='/work/libcamera225-built/src/libcamera-v0.7.2'
command=['chroot',str(sdk),'/usr/bin/g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-DLIBCAMERA_PRIVATE','-DLIBCAMERA_BASE_PRIVATE',
 '-include',b+'/output/config.h','-I'+b,'-I'+b+'/include','-I'+b+'/output/include','-I'+b+'/src/ipa','-I'+b+'/src/ipa/simple','-I'+b+'/output/include/libcamera/ipa','-I'+b+'/output/include/libcamera',
 '/private/agc-control-regression225.cpp',b+'/src/ipa/simple/algorithms/agc.cpp',b+'/output/src/ipa/libipa/libipa.a',
 '-L'+b+'/output/src/libcamera','-L'+b+'/output/src/libcamera/base','-lcamera','-lcamera-base','-o','/private/agc-control-regression225']
p=subprocess.run(command,capture_output=True,timeout=180);(private/'agc-regression-build-private.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0
env='LD_LIBRARY_PATH='+b+'/output/src/libcamera:'+b+'/output/src/libcamera/base'
p=subprocess.run(['chroot',str(sdk),'/usr/bin/env',env,'/private/agc-control-regression225'],capture_output=True,timeout=40)
(private/'agc-regression-run-private.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0
r=json.loads(p.stdout);assert r['passed'] and r['behavioral_assertions']>=40
r.update(stage=225,real_new_algorithm_compiled=True,arm_emulated_behavioral_test=True,
 source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
 independent_auto_manual_ignore_freeze_resume_mixed_bounds_and_capture_source_verified=True,
 camera_core_ae_enable_preprocessing_and_physical_delay_not_tested_here=True,no_phone_mutation=True)
(here/'agc-control-regression-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
