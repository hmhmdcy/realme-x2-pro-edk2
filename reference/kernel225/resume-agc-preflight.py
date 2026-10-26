"""Resume the independent compile after correcting its missing private include."""
from pathlib import Path
import hashlib,json,subprocess

here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel225');sdk=Path('/home/cy122/x2pro-linux/libcamera214-root')
assert 'libipa/algorithm.h: No such file' in (private/'agc-preflight-build-private.log').read_text()
expected=json.loads((here/'candidate-source-validation.json').read_text())['source_files']['src/ipa/simple/algorithms/agc.cpp']
choices=['/work/libcamera/src/libcamera-v0.7.2','/work/libcamera225-built/src/libcamera-v0.7.2']
choices=[b for b in choices if (sdk/b.lstrip('/')/'src/ipa/simple/algorithms/agc.cpp').is_file() and hashlib.sha256((sdk/b.lstrip('/')/'src/ipa/simple/algorithms/agc.cpp').read_bytes()).hexdigest()==expected]
assert len(choices)==1;b=choices[0]
test=sdk/'private/agc-control-preflight225.cpp';assert test.read_bytes()==(here/'agc-control-regression.cpp').read_bytes()
command=['chroot',str(sdk),'/usr/bin/g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-DLIBCAMERA_PRIVATE','-DLIBCAMERA_BASE_PRIVATE',
 '-include',b+'/output/config.h','-I'+b,'-I'+b+'/include','-I'+b+'/output/include','-I'+b+'/src/ipa','-I'+b+'/src/ipa/simple','-I'+b+'/output/include/libcamera/ipa','-I'+b+'/output/include/libcamera',
 '/private/agc-control-preflight225.cpp',b+'/src/ipa/simple/algorithms/agc.cpp','/private/libipa-agc-preflight225.a',
 '-L/candidate224-r11/usr/lib','-lcamera','-lcamera-base','-o','/private/agc-control-preflight225']
p=subprocess.run(command,capture_output=True,timeout=180);(private/'agc-preflight-build-r3-private.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0
p=subprocess.run(['chroot',str(sdk),'/usr/bin/env','LD_LIBRARY_PATH=/candidate224-r11/usr/lib','/private/agc-control-preflight225'],capture_output=True,timeout=40)
(private/'agc-preflight-run-private.log').write_bytes(p.stdout+p.stderr)
r=dict(stage=225,standalone_actual_new_agc_compiled=True,stable_r11_core_base_used_for_algorithm_only=True,
 actual_agc_source_sha256=expected,run_exit=p.returncode,failed_latest_target_hold_requirement=b'invalid statistics must hold the latest computed targets' in p.stderr,
 preflight_include_path_corrected=True,initial_compile_diagnostic_retained=True,full_build_not_interrupted=True,phone_unchanged=True)
(here/'agc-preflight-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
assert p.returncode==1 and r['failed_latest_target_hold_requirement']
