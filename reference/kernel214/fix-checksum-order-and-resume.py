from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,time
os.umask(0o077);here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel214');root=Path('/home/cy122/x2pro-linux/libcamera214-root');port=repo/'linux-port/packages/libcamera';recipe=port/'APKBUILD'
result=json.loads((private/'full-libcamera-build-result-private.json').read_text());assert result['abuild_exit']==1 and not result['packages'];old_job=json.loads((private/'active-camera-build-private.json').read_text());assert not Path('/proc',str(old_job['pid'])).exists()
assert not (root/'work/libcamera/src/libcamera-v0.7.2/output').exists()
text=recipe.read_text();(private/'APKBUILD-before-checksum-order-private').write_text(text)
source=subprocess.check_output(['chroot',str(root),'/usr/bin/env','CARCH=aarch64','/bin/ash','-c','. /work/libcamera/APKBUILD; printf "%s\\n" $source'],text=True).splitlines()
pairs=re.findall(r'(?m)^([0-9a-f]{128})  ([^\n]+)$',text);checks={name:digest for digest,name in pairs};assert len(checks)==len(pairs)==len(source)
names=[uri.rsplit('/',1)[-1] for uri in source];assert set(names)==set(checks)
for name in names:
    path=(root/'var/cache/distfiles'/name) if name.endswith('.tar.gz') else port/name
    assert hashlib.sha512(path.read_bytes()).hexdigest()==checks[name],name
assert [name for _,name in pairs]!=names
text=text.split('sha512sums="',1)[0]+'sha512sums="\n'+''.join(checks[name]+'  '+name+'\n' for name in names)+'"\n';recipe.write_text(text)
for path in [port/'source-lock.json',here/'full-port-source-validation.json']:
    report=json.loads(path.read_text());report['source_files_sha256']['APKBUILD']=hashlib.sha256(recipe.read_bytes()).hexdigest();report['checksums_follow_source_order']=True;path.write_text(json.dumps(report,indent=2)+'\n')
shutil.copyfile(recipe,root/'work/libcamera/APKBUILD')
report=dict(stage=214,first_build_failed_before_compile=True,cause='New patch entries inserted before tuning in source but checksums appended after tuning; abuild pairs checksums positionally',all_input_sha512_independently_verified=True,source_and_checksum_order_now_match=True,initial_failure_log_preserved=True,no_device_mutation=True)
(here/'checksum-order-repair-validation.json').write_text(json.dumps(report,indent=2)+'\n')
command=['chroot',str(root),'/usr/bin/env','LIBCAMERA_IPA_PRIVATE_KEY=/private/ipa214.rsa.pem','SOURCE_DATE_EPOCH=1792022400','JOBS=4','/bin/ash','-c','cd /work/libcamera && umask 022 && exec /usr/bin/abuild -F -d all']
log=private/'full-libcamera-build-r2-private.log';assert not log.exists()
with log.open('wb') as output:
    process=subprocess.Popen(command,stdout=output,stderr=subprocess.STDOUT)
    (private/'active-camera-build-private.json').write_text(json.dumps(dict(pid=process.pid,phase='full-libcamera-abuild-r2',root=str(root),started_monotonic=time.monotonic()),indent=2)+'\n')
    result=process.wait(timeout=7200)
record=dict(stage=214,abuild_exit=result,full_build_finished=True,phone_not_modified=True,packages=[p.name for p in (root/'packages').rglob('*.apk')])
(private/'full-libcamera-build-r2-result-private.json').write_text(json.dumps(record,indent=2)+'\n')
assert result==0,'Inspect existing build state/log; do not restart blindly'
(here/'full-libcamera-build-validation.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
