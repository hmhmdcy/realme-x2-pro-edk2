"""Test GW1 factory from the real r21 build, with r20 as a negative control."""
from pathlib import Path
import hashlib,json,shutil,subprocess
import host
R=Path(__file__).resolve().parent;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
assert json.loads((R/'r21-package-build-validation.json').read_text())['framework_and_config_packages_built']
source=SDK/'private/gain-helper273.cpp';assert not source.exists();shutil.copyfile(R.parent/'kernel272/gain-helper-test.cpp',source)
results={}
for label,tree in [('r21','libcamera273-r21-built'),('negative-r20','libcamera271-r20-built')]:
 b='/work/'+tree+'/src/libcamera-v0.7.2';target='/private/gain-helper273-'+label
 cmd=['chroot',str(SDK),'/usr/bin/g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-DLIBCAMERA_PRIVATE','-DLIBCAMERA_BASE_PRIVATE',
 '-include',b+'/output/config.h','-I'+b+'/include','-I'+b+'/output/include','-I'+b+'/src/ipa','-I'+b+'/output/include/libcamera/ipa',
 '-I'+b+'/output/include/libcamera','/private/gain-helper273.cpp',b+'/output/src/ipa/libipa/libipa.a',
 '-L'+b+'/output/src/libcamera','-L'+b+'/output/src/libcamera/base','-lcamera','-lcamera-base','-o',target]
 q=subprocess.run(cmd,capture_output=True,timeout=180);(host.PRIVATE/(label+'-helper-build-private.log')).write_bytes(q.stdout+q.stderr);assert q.returncode==0
 q=subprocess.run(['chroot',str(SDK),'/usr/bin/env','LD_LIBRARY_PATH='+b+'/output/src/libcamera:'+b+'/output/src/libcamera/base',target],capture_output=True,timeout=30)
 (host.PRIVATE/(label+'-helper-run-private.log')).write_bytes(q.stdout+q.stderr);assert q.returncode==(0 if label=='r21' else 3)
 results[label]=dict(exit=q.returncode,report=json.loads(q.stdout) if q.stdout else None)
report=dict(stage=273,actual_r21_static_libipa_factory_test=True,arm_emulated_cpp=True,results=results,
 source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),negative_r20_missing_gw1_verified=True,phone_unchanged=True)
(R/'built-helper-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
