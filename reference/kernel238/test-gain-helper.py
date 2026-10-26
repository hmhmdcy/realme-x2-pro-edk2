from pathlib import Path
import hashlib,json,shutil,subprocess
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel238');SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
assert json.loads((R/'package-build-validation.json').read_text())['framework_and_config_packages_built']
source=SDK/'private/gain-helper-test238.cpp';assert not source.exists();shutil.copyfile(R/'gain-helper-test.cpp',source)
results={}
for label,tree in [('r14','libcamera238-r14-built'),('negative-r13','libcamera225-r13-built')]:
 b='/work/'+tree+'/src/libcamera-v0.7.2';target='/private/gain-helper-test238-'+label
 cmd=['chroot',str(SDK),'/usr/bin/g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-DLIBCAMERA_PRIVATE','-DLIBCAMERA_BASE_PRIVATE','-include',b+'/output/config.h','-I'+b+'/include','-I'+b+'/output/include','-I'+b+'/src/ipa','-I'+b+'/output/include/libcamera/ipa','-I'+b+'/output/include/libcamera','/private/gain-helper-test238.cpp',b+'/output/src/ipa/libipa/libipa.a','-L'+b+'/output/src/libcamera','-L'+b+'/output/src/libcamera/base','-lcamera','-lcamera-base','-o',target]
 p=subprocess.run(cmd,capture_output=True,timeout=180);(P/(label+'-helper-build-private.log')).write_bytes(p.stdout+p.stderr);assert p.returncode==0
 p=subprocess.run(['chroot',str(SDK),'/usr/bin/env','LD_LIBRARY_PATH='+b+'/output/src/libcamera:'+b+'/output/src/libcamera/base',target],capture_output=True,timeout=30);(P/(label+'-helper-run-private.log')).write_bytes(p.stdout+p.stderr)
 assert p.returncode==(0 if label=='r14' else 3)
 results[label]=dict(exit=p.returncode,report=json.loads(p.stdout) if p.stdout else None)
report=dict(stage=238,real_static_libipa_factory_test=True,arm_emulated_cpp=True,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),results=results,negative_r13_missing_helper_verified=True,no_phone_mutation=True)
(R/'gain-helper-test-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
