from pathlib import Path
import hashlib,json,os,subprocess,time
os.umask(0o077);here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel214');root=Path('/home/cy122/x2pro-linux/libcamera214-root')
assert json.loads((here/'build-environment-validation.json').read_text())['host_arm_build_environment_ready']
lock=json.loads((repo/'linux-port/packages/libcamera/source-lock.json').read_text());assert all(hashlib.sha256((root/'work/libcamera'/name).read_bytes()).hexdigest()==digest for name,digest in lock['source_files_sha256'].items())
assert not (root/'work/libcamera/src').exists()
command=['chroot',str(root),'/usr/bin/env','LIBCAMERA_IPA_PRIVATE_KEY=/private/ipa214.rsa.pem','SOURCE_DATE_EPOCH=1792022400','JOBS=4','/bin/ash','-c','cd /work/libcamera && umask 022 && exec /usr/bin/abuild -F -d all']
log=private/'full-libcamera-build-private.log';assert not log.exists()
with log.open('wb') as output:
    process=subprocess.Popen(command,stdout=output,stderr=subprocess.STDOUT)
    (private/'active-camera-build-private.json').write_text(json.dumps(dict(pid=process.pid,phase='full-libcamera-abuild',root=str(root),started_monotonic=time.monotonic()),indent=2)+'\n')
    result=process.wait(timeout=7200)
report=dict(stage=214,abuild_exit=result,full_build_finished=True,phone_not_modified=True,packages=[p.name for p in (root/'packages').rglob('*.apk')])
(private/'full-libcamera-build-result-private.json').write_text(json.dumps(report,indent=2)+'\n')
assert result==0,'Full build exited; inspect logs and resume existing state, do not restart blindly'
(here/'full-libcamera-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
