"""Compile only AGC against stable r11 public libraries while full r12 builds."""
from pathlib import Path
import hashlib,json,shutil,subprocess

here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel225');sdk=Path('/home/cy122/x2pro-linux/libcamera214-root')
state=json.loads((private/'r12-build-repair1-state-private.json').read_text())
assert state['phase']=='full-feature-r12-repair1-build-live' and Path('/proc',str(state['pid'])).exists()
b='/work/libcamera/src/libcamera-v0.7.2';source=sdk/b.lstrip('/')/'src/ipa/simple/algorithms/agc.cpp'
expected=json.loads((here/'candidate-source-validation.json').read_text())['source_files']['src/ipa/simple/algorithms/agc.cpp']
assert hashlib.sha256(source.read_bytes()).hexdigest()==expected
test=sdk/'private/agc-control-preflight225.cpp';assert not test.exists();shutil.copyfile(here/'agc-control-regression.cpp',test)
archive=sdk/'private/libipa-agc-preflight225.a';assert not archive.exists();shutil.copyfile(sdk/b.lstrip('/')/'output/src/ipa/libipa/libipa.a',archive)
command=['chroot',str(sdk),'/usr/bin/g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-DLIBCAMERA_PRIVATE','-DLIBCAMERA_BASE_PRIVATE',
 '-include',b+'/output/config.h','-I'+b,'-I'+b+'/include','-I'+b+'/output/include','-I'+b+'/src/ipa','-I'+b+'/src/ipa/simple','-I'+b+'/output/include/libcamera/ipa','-I'+b+'/output/include/libcamera',
 '/private/agc-control-preflight225.cpp',b+'/src/ipa/simple/algorithms/agc.cpp','/private/libipa-agc-preflight225.a',
 '-L/candidate224-r11/usr/lib','-lcamera','-lcamera-base','-o','/private/agc-control-preflight225']
p=subprocess.run(command,capture_output=True,timeout=180);(private/'agc-preflight-build-private.log').write_bytes(p.stdout+p.stderr)
assert hashlib.sha256(source.read_bytes()).hexdigest()==expected
assert p.returncode==0,'Inspect preflight compile log; full build remains independent'
p=subprocess.run(['chroot',str(sdk),'/usr/bin/env','LD_LIBRARY_PATH=/candidate224-r11/usr/lib','/private/agc-control-preflight225'],capture_output=True,timeout=40)
(private/'agc-preflight-run-private.log').write_bytes(p.stdout+p.stderr)
r=dict(stage=225,standalone_actual_new_agc_compiled=True,stable_r11_core_base_used_for_algorithm_only=True,
 actual_agc_source_sha256=expected,run_exit=p.returncode,failed_latest_target_hold_requirement=b'invalid statistics must hold the latest computed targets' in p.stderr,
 full_build_not_interrupted=True,phone_unchanged=True)
(here/'agc-preflight-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
assert p.returncode==1 and r['failed_latest_target_hold_requirement']
