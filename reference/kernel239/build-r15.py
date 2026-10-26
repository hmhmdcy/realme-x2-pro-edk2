"""Full signed r15/r10 from retained r14 cache, restoring all original214 inputs."""
from pathlib import Path
import hashlib,json,os,shutil,stat,subprocess,time
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel239');SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
work=SDK/'work/libcamera';snapshot=SDK/'private/libcamera214-before239-r15';retained=SDK/'work/libcamera239-r15-built';cache=SDK/'work/libcamera238-r14-built';recipe=SDK/'work/libcamera239-r15'
proof=json.loads((R/'r15-source-validation.json').read_text());assert proof['patch_count']==22
assert work.is_dir() and cache.is_dir() and (recipe/'0022-soft-initial-parameters.patch').is_file() and (SDK/'work/samurai-camera-config239-r15/APKBUILD').is_file()
assert not any(p.exists() for p in [snapshot,retained,SDK/'packages239-r15',SDK/'packages-config239-r15'])
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
cache_before=inventory(cache);(P/'r14-cache-before-private.json').write_text(json.dumps(cache_before,indent=2)+'\n')
state=dict(stage=239,phase='snapshot-submitted',original=str(work),snapshot=str(snapshot),candidate=str(retained),started=time.time());marker=P/'r15-build-state-private.json'
def record(**kw):state.update(kw);marker.write_text(json.dumps(state,indent=2)+'\n')
record();os.rename(work,snapshot);process=None;ret=None
try:
 record(phase='retained-r14-cache-copy-live');shutil.copytree(cache,work,symlinks=True,ignore=lambda d,n:[x for x in n if x=='pkg' or x.startswith('pkg-before')])
 for p in recipe.iterdir():
  if p.is_file():shutil.copyfile(p,work/p.name)
 source=work/'src/libcamera-v0.7.2'
 assert all(hashlib.sha256((source/n).read_bytes()).hexdigest()==h for n,h in proof['source_before_files'].items())
 result=subprocess.run(['patch','--batch','--forward','-p1','-i',str(work/'0022-soft-initial-parameters.patch')],cwd=source,capture_output=True,timeout=20)
 (P/'r15-patch-apply-private.log').write_bytes(result.stdout+result.stderr);assert result.returncode==0
 assert all(hashlib.sha256((source/n).read_bytes()).hexdigest()==h for n,h in proof['source_files'].items())
 checked=0
 for line in (work/'APKBUILD').read_text().split('sha512sums="',1)[1].split('"',1)[0].splitlines():
  if not line.strip():continue
  digest,name=line.split(maxsplit=1);p=work/name
  if not p.exists():p=work/'src'/name
  if p.is_symlink() and os.path.isabs(os.readlink(p)):p=SDK/os.readlink(p).lstrip('/')
  assert p.is_file() and hashlib.sha512(p.read_bytes()).hexdigest()==digest,name;checked+=1
 command=['chroot',str(SDK),'/usr/bin/env','LIBCAMERA_IPA_PRIVATE_KEY=/private/ipa214.rsa.pem','SOURCE_DATE_EPOCH=1792022400','JOBS=4','/bin/ash','-c','cd /work/libcamera && umask 022 && exec /usr/bin/abuild -F -d -K -P /packages239-r15 build rootpkg index']
 with (P/'full-r15-build-private.log').open('xb') as log:
  process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT);record(phase='full-feature-r15-build-live',pid=process.pid,source_inputs_verified=checked);ret=process.wait()
 record(phase='framework-terminal-restoration-pending',exit=ret)
finally:
 if process is None or process.poll() is not None:
  if work.exists():os.rename(work,retained)
  assert snapshot.exists() and not work.exists();os.rename(snapshot,work);assert inventory(work)==original
  record(original214_files_links_modes_restored=True,candidate_source_objects_retained=True)
assert ret==0,'Inspect terminal build failure before continuation'
assert len(list((SDK/'packages239-r15').rglob('*.apk')))==11
record(phase='framework-complete-config-build-next')
with (P/'config-r10-build-private.log').open('xb') as log:
 result=subprocess.run(['chroot',str(SDK),'/usr/bin/env','SOURCE_DATE_EPOCH=1792022400','/bin/ash','-c','cd /work/samurai-camera-config239-r15 && umask 022 && exec /usr/bin/abuild -F -d -K -P /packages-config239-r15 all'],stdout=log,stderr=subprocess.STDOUT)
assert result.returncode==0 and len(list((SDK/'packages-config239-r15').rglob('*.apk')))==2
assert inventory(cache)==cache_before
record(phase='all13-r15-r10-packages-built-original214-restored',terminal=True)
report=dict(stage=239,framework_and_config_packages_built=True,package_count=13,full_feature_targets_and_prior21_patches_retained=True,official_abuild_build_rootpkg_index_used=True,original214_files_links_modes_restored=len(original),r14_cache_files_unchanged=len(cache_before),candidate_full_sources_and_objects_retained=True,original_signing_inputs_reused=True,phone_not_modified_by_build=True)
(R/'r15-package-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
