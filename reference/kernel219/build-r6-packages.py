from pathlib import Path
import json,os,subprocess,time

os.umask(0o077);here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel219')
root=Path('/home/cy122/x2pro-linux/libcamera214-root')
assert json.loads((here/'r6-package-source-validation.json').read_text())['original_full_feature_set_and_all_subpackages_retained']
assert not (root/'packages219').exists() and not (root/'packages-config219').exists()
command=['chroot',str(root),'/usr/bin/env','LIBCAMERA_IPA_PRIVATE_KEY=/private/ipa214.rsa.pem','SOURCE_DATE_EPOCH=1792022400','JOBS=4',
         '/bin/ash','-c','cd /work/libcamera219 && umask 022 && exec /usr/bin/abuild -F -d -P /packages219 all']
with (private/'full-r6-build-private.log').open('xb') as log:
    process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
    (private/'active-r6-build-private.json').write_text(json.dumps(dict(pid=process.pid,started=time.time(),root=str(root),command=command),indent=2)+'\n')
    code=process.wait(timeout=7200)
assert code==0,'Inspect existing r6 build log and outputs; do not restart from scratch'
command=['chroot',str(root),'/usr/bin/env','SOURCE_DATE_EPOCH=1792022400','/bin/ash','-c','cd /work/samurai-camera-config219 && umask 022 && exec /usr/bin/abuild -F -d -K -P /packages-config219 all']
with (private/'r1-config-build-private.log').open('xb') as log:
    process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
    (private/'active-r6-build-private.json').write_text(json.dumps(dict(pid=process.pid,started=time.time(),root=str(root),command=command),indent=2)+'\n')
    code=process.wait(timeout=180)
assert code==0,'Inspect config package build log'
packages=list((root/'packages219').rglob('*.apk'))+list((root/'packages-config219').rglob('*.apk'))
assert len(packages)==13,len(packages)
report=dict(stage=219,framework_and_device_config_packages_built=True,package_count=13,packages=[p.name for p in packages],
            private_signing_inputs_reused=True,phone_packages_not_replaced=True,signature_payload_runtime_validation_pending=True)
(here/'r6-package-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
