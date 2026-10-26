from pathlib import Path
import json,os,shutil,subprocess
here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel214');root=Path('/home/cy122/x2pro-linux/libcamera214-root');prefix=Path('/home/cy122/x2pro-linux/libcamera214-qa-prefix');destination=root/'candidate';assert not destination.exists();shutil.copytree(prefix,destination,symlinks=True)
runtime=root/'tmp/k214-runtime';runtime.mkdir(mode=0o700)
base=['chroot',str(root),'/usr/bin/env','LD_LIBRARY_PATH=/candidate/usr/lib','PYTHONPATH=/candidate/usr/lib/python3.14/site-packages','QT_QPA_PLATFORM=offscreen','XDG_RUNTIME_DIR=/tmp/k214-runtime']
tests=[]
for label,args in [('cam-help',['/candidate/usr/bin/cam','--help']),('lc-compliance-help',['/candidate/usr/bin/lc-compliance','--help']),('qcam-offscreen-help',['/candidate/usr/bin/qcam','--help']),('python-binding-import',['/usr/bin/python3','-c','import libcamera; print(libcamera.__name__)'])]:
    p=subprocess.run([*base,*args],capture_output=True,text=True,timeout=60);(private/(label+'-host-runtime-private.log')).write_text(p.stdout+p.stderr);tests.append(dict(name=label,exit=p.returncode,passed=p.returncode==0))
verify='/work/libcamera/src/libcamera-v0.7.2/output/src/apps/ipa-verify/ipa_verify';ipas=[]
for path in sorted((destination/'usr/lib/libcamera/ipa').glob('*.so')):
    p=subprocess.run([*base,verify,'/'+str(path.relative_to(root))],capture_output=True,text=True,timeout=30);(private/(path.name+'-embedded-key-verify-private.log')).write_text(p.stdout+p.stderr);ipas.append(dict(module=path.name,exit=p.returncode,valid=p.returncode==0 and 'IPA module signature is valid' in p.stdout))
report=dict(stage=214,host_arm_emulation_runtime_checks=tests,packaged_ipa_signatures_verified_against_core_embedded_key=ipas,all_five_ipa_signatures_valid=len(ipas)==5 and all(p['valid'] for p in ipas),physical_camera_not_tested_by_host_emulation=True,no_device_mutation=True)
(here/'host-runtime-qa-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));assert all(t['passed'] for t in tests) and report['all_five_ipa_signatures_valid']
