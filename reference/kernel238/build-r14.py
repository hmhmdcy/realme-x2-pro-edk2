"""Full abuild r14/r9 from r13 object cache; restore original214 on terminal."""
from pathlib import Path
import hashlib,json,os,shutil,stat,subprocess,time
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel238');SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
work=SDK/'work/libcamera';snapshot=SDK/'private/libcamera214-before238-r14';retained=SDK/'work/libcamera238-r14-built';cache=SDK/'work/libcamera225-r13-built';recipe=SDK/'work/libcamera238-r14'
assert work.is_dir() and cache.is_dir() and not any(p.exists() for p in [snapshot,retained,SDK/'packages238-r14'])
assert recipe.is_dir() and (recipe/'0021-imx319-gain-helper.patch').is_file() and (R/'helper-source-validation.json').is_file()
assert (SDK/'work/samurai-camera-config238-r14/APKBUILD').is_file()
for p in [work,snapshot,retained,cache,recipe]:assert p.parent.resolve().is_relative_to(SDK.resolve()) and not p.is_symlink()
for p in Path('/proc').glob('[0-9]*'):
 try:
  if (p/'comm').read_text().strip() in ['ninja','meson','abuild','cc1plus']:assert not p.joinpath('cwd').resolve().is_relative_to(work),'Existing SDK build live'
 except (FileNotFoundError,ProcessLookupError):pass
def inventory(directory):
 result={}
 for p in directory.rglob('*'):
  if p.is_symlink():result[str(p.relative_to(directory))]=dict(target=os.readlink(p))
  elif p.is_file():result[str(p.relative_to(directory))]=dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),mode=stat.S_IMODE(p.stat().st_mode))
 return result
original=inventory(work);assert original==json.loads((P.parent/'kernel220/original214-work-manifest-private.json').read_text())
(P/'original214-work-manifest-private.json').write_text(json.dumps(original,indent=2)+'\n')
state=dict(stage=238,phase='snapshot-submitted',original=str(work),snapshot=str(snapshot),candidate=str(retained),started=time.time());marker=P/'r14-build-state-private.json'
def record(**kw):state.update(kw);marker.write_text(json.dumps(state,indent=2)+'\n')
record();os.rename(work,snapshot);process=None;ret=None
try:
 record(phase='retained-r13-cache-copy-live');shutil.copytree(cache,work,symlinks=True,ignore=lambda d,n:[x for x in n if x=='pkg' or x.startswith('pkg-before')])
 for p in recipe.iterdir():
  if p.is_file():shutil.copyfile(p,work/p.name)
 source=work/'src/libcamera-v0.7.2';proof=json.loads((R/'helper-source-validation.json').read_text());assert hashlib.sha256((source/'src/ipa/libipa/camera_sensor_helper.cpp').read_bytes()).hexdigest()==proof['source_before_sha256']
 p=subprocess.run(['patch','--batch','--forward','-p1','-i',str(work/'0021-imx319-gain-helper.patch')],cwd=source,capture_output=True,timeout=20);(P/'helper-apply-private.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0
 assert all(hashlib.sha256((source/n).read_bytes()).hexdigest()==h for n,h in proof['source_files'].items())
 checked=0
 for line in (work/'APKBUILD').read_text().split('sha512sums="',1)[1].split('"',1)[0].splitlines():
  if not line.strip():continue
  digest,name=line.split(maxsplit=1);p=work/name
  if not p.exists():p=work/'src'/name
  if p.is_symlink() and os.path.isabs(os.readlink(p)):p=SDK/os.readlink(p).lstrip('/')
  assert p.is_file() and hashlib.sha512(p.read_bytes()).hexdigest()==digest,name;checked+=1
 cmd=['chroot',str(SDK),'/usr/bin/env','LIBCAMERA_IPA_PRIVATE_KEY=/private/ipa214.rsa.pem','SOURCE_DATE_EPOCH=1792022400','JOBS=4','/bin/ash','-c','cd /work/libcamera && umask 022 && exec /usr/bin/abuild -F -d -K -P /packages238-r14 build rootpkg index']
 with (P/'full-r14-build-private.log').open('xb') as log:
  process=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT);record(phase='full-feature-r14-build-live',pid=process.pid,source_inputs_verified=checked)
  ret=process.wait()
 record(phase='framework-terminal-restoration-pending',exit=ret)
finally:
 if process is None or process.poll() is not None:
  if work.exists():os.rename(work,retained)
  assert snapshot.exists() and not work.exists();os.rename(snapshot,work);assert inventory(work)==original
  record(original214_files_links_modes_restored=True,candidate_source_objects_retained=True)
assert ret==0,'Inspect terminal build before any continuation'
assert len(list((SDK/'packages238-r14').rglob('*.apk')))==11
record(phase='framework-complete-config-build-next')
with (P/'config-r9-build-private.log').open('xb') as log:
 p=subprocess.run(['chroot',str(SDK),'/usr/bin/env','SOURCE_DATE_EPOCH=1792022400','/bin/ash','-c','cd /work/samurai-camera-config238-r14 && umask 022 && exec /usr/bin/abuild -F -d -K -P /packages-config238-r14 all'],stdout=log,stderr=subprocess.STDOUT)
assert p.returncode==0 and len(list((SDK/'packages-config238-r14').rglob('*.apk')))==2
record(phase='all13-r14-r9-packages-built-original214-restored',terminal=True)
report=dict(stage=238,framework_and_config_packages_built=True,package_count=13,full_feature_targets_and_prior20_patches_retained=True,official_abuild_build_rootpkg_index_used=True,original214_files_links_modes_restored=len(original),r13_object_cache_preserved=True,candidate_full_sources_and_objects_retained=True,original_signing_inputs_reused=True,phone_not_modified_by_build=True)
(R/'package-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
