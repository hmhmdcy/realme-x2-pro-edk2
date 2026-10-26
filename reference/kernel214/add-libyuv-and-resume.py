from pathlib import Path
import hashlib,json,os,shutil,subprocess,time
os.umask(0o077);here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel214');root=Path('/home/cy122/x2pro-linux/libcamera214-root');port=repo/'linux-port/packages/libcamera'
old=json.loads((private/'full-libcamera-build-r2-result-private.json').read_text());assert old['abuild_exit']==1 and not old['packages'];active=json.loads((private/'active-camera-build-private.json').read_text());assert not Path('/proc',str(active['pid'])).exists()
source=root/'work/libcamera/src/libcamera-v0.7.2';lock=json.loads((repo/'linux-port/camera/libcamera/source-lock.json').read_text());assert all(hashlib.sha256((source/name).read_bytes()).hexdigest()==digest for name,digest in lock['source_files_sha256'].items())
assert not list((root/'usr/lib').glob('*yuv*'))
apk=Path('/home/cy122/pmos-samurai-rootfs01/work/apk.static');keys=Path('/home/cy122/pmos-samurai-rootfs01/work/config_apk_keys')
with (private/'add-libyuv-runtime-private.log').open('xb') as log:subprocess.run([str(apk),'--root',str(root),'--arch','aarch64','--keys-dir',str(keys),'--repositories-file',str(private/'build-repositories-private.list'),'--no-cache','--no-scripts','add','libyuv'],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
assert (root/'usr/lib/libyuv.so').is_file()
recipe=port/'APKBUILD';text=recipe.read_text();assert text.count('\tlibyuv-dev\n')==1;text=text.replace('\tlibyuv-dev\n','\tlibyuv\n\tlibyuv-dev\n');recipe.write_text(text)
for path in [port/'source-lock.json',here/'full-port-source-validation.json']:
    report=json.loads(path.read_text());report['source_files_sha256']['APKBUILD']=hashlib.sha256(recipe.read_bytes()).hexdigest();report['unversioned_libyuv_runtime_explicit_build_dependency']=True;path.write_text(json.dumps(report,indent=2)+'\n')
shutil.copyfile(recipe,root/'work/libcamera/APKBUILD')
repair=dict(stage=214,second_build_failed_at_configure_before_ninja=True,libyuv_headers_present_but_unversioned_runtime_library_absent=True,real_signed_libyuv_runtime_added_to_isolated_root=True,recipe_explicit_dependency_added=True,original_processing_source_hashes_unchanged=True,existing_source_and_failed_configuration_preserved=True,no_device_mutation=True)
(here/'libyuv-dependency-repair-validation.json').write_text(json.dumps(repair,indent=2)+'\n')
command=['chroot',str(root),'/usr/bin/env','LIBCAMERA_IPA_PRIVATE_KEY=/private/ipa214.rsa.pem','SOURCE_DATE_EPOCH=1792022400','JOBS=4','/bin/ash','-c','cd /work/libcamera && umask 022 && exec /usr/bin/abuild -F -d build rootpkg']
with (private/'full-libcamera-build-r3-private.log').open('xb') as output:
    process=subprocess.Popen(command,stdout=output,stderr=subprocess.STDOUT)
    (private/'active-camera-build-private.json').write_text(json.dumps(dict(pid=process.pid,phase='full-libcamera-abuild-r3',root=str(root),started_monotonic=time.monotonic()),indent=2)+'\n')
    result=process.wait(timeout=7200)
record=dict(stage=214,abuild_exit=result,full_build_finished=True,phone_not_modified=True,packages=[p.name for p in (root/'packages').rglob('*.apk')]);(private/'full-libcamera-build-r3-result-private.json').write_text(json.dumps(record,indent=2)+'\n')
assert result==0,'Inspect existing native host build state; do not restart blindly'
(here/'full-libcamera-build-validation.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
