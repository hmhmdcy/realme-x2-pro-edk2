from pathlib import Path
import json,subprocess,shutil
import host
HERE=Path(__file__).resolve().parent
SDK=Path('/home/cy122/x2pro-linux/libcamera214-root');stage=SDK/'private/camss319-test'
for p in [HERE/'libipa/lsc_resample.h',HERE/'libipa/lsc_resample.cpp',HERE/'test-resample.cpp',HERE.parent/'kernel317/libipa/lens_shading.h']:
 target=stage/p.relative_to(HERE.parent);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
results={}
for arch in ['host','aarch64']:
 binary=host.PRIVATE/('test-resample-'+arch)
 flags=['-std=c++17','-O2','-Wall','-Wextra','-Werror']
 if arch=='host':args=['g++',*flags,str(HERE/'libipa/lsc_resample.cpp'),str(HERE/'test-resample.cpp'),'-o',str(binary)];runner=[str(binary)]
 else:
  args=['chroot',str(SDK),'g++',*flags,'/private/camss319-test/kernel319/libipa/lsc_resample.cpp','/private/camss319-test/kernel319/test-resample.cpp','-o','/private/camss319-test/test-resample']
  runner=['chroot',str(SDK),'/private/camss319-test/test-resample']
 q=subprocess.run(args,capture_output=True)
 (host.PRIVATE/('build-'+arch+'.log')).write_bytes(q.stdout+q.stderr)
 assert q.returncode==0,q.stderr.decode()
 if arch=='aarch64':shutil.copyfile(stage/'test-resample',binary)
 q=subprocess.run(runner,capture_output=True)
 (host.PRIVATE/('test-'+arch+'.log')).write_bytes(q.stdout+q.stderr)
 assert q.returncode==0,q.stdout.decode()+q.stderr.decode()
 results[arch]={'werror_build':True,'test_passed':True,'output':q.stdout.decode().strip()}
report=dict(stage=319,architectures=results,passed=True,phone_changed=False,ipa_integrated=False)
(HERE/'resample-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
