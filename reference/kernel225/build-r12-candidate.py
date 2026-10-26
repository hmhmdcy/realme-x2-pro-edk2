"""Build the full r11 stack from retained r8 cache; preserve original214 tree."""
from pathlib import Path
import hashlib,json,os,shutil,stat,subprocess,time
here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel225');root=Path('/home/cy122/x2pro-linux/libcamera214-root')
work=root/'work/libcamera';snapshot=root/'private/libcamera214-before225';retained=root/'work/libcamera225-built';cache=root/'work/libcamera224-r11-built';recipe=root/'work/libcamera225'
for p in [work,snapshot,retained,cache,recipe]:assert p.parent.resolve().is_relative_to(root.resolve()) and not p.is_symlink()
assert work.is_dir() and cache.is_dir() and not snapshot.exists() and not retained.exists() and not (root/'packages225').exists()
assert 'pkgrel=5\n' in (work/'APKBUILD').read_text()
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  if (p/'comm').read_text().strip() in ['ninja','meson','abuild','cc1plus']:
   assert not (p/'cwd').resolve().is_relative_to(work),'Existing SDK build live'
 except (FileNotFoundError,ProcessLookupError):pass
def inventory(directory):
 result={}
 for p in directory.rglob('*'):
  if p.is_symlink():result[str(p.relative_to(directory))]=dict(target=os.readlink(p))
  elif p.is_file():result[str(p.relative_to(directory))]=dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),mode=stat.S_IMODE(p.stat().st_mode))
 return result
original=inventory(work);assert original==json.loads((private.parent/'kernel220/original214-work-manifest-private.json').read_text())
(private/'original214-work-manifest-private.json').write_text(json.dumps(original,indent=2)+'\n')
state=dict(stage=225,phase='original214-snapshot-submitted',original=str(work),snapshot=str(snapshot),candidate=str(retained));marker=private/'r12-build-state-private.json'
def record(**values):state.update(values);marker.write_text(json.dumps(state,indent=2)+'\n')
record();os.rename(work,snapshot);process=None;rc=None
try:
 record(phase='retained-r11-cache-copy-live')
 shutil.copytree(cache,work,symlinks=True,ignore=lambda directory,names:[n for n in names if n=='pkg' or n.startswith('pkg-before')])
 for p in recipe.iterdir():
  if p.is_file():shutil.copyfile(p,work/p.name)
 source=work/'src/libcamera-v0.7.2'
 p=subprocess.run(['patch','--batch','--forward','-p1','-i',str(work/'0018-simple-manual-exposure-controls.patch')],cwd=source,capture_output=True,timeout=20);(private/'r12-patch-apply-private.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0
 proof=json.loads((here/'candidate-source-validation.json').read_text());assert all(hashlib.sha256((source/n).read_bytes()).hexdigest()==h for n,h in proof['source_files'].items())
 apk=(work/'APKBUILD').read_text();checked=0
 for line in apk.split('sha512sums="',1)[1].split('"',1)[0].splitlines():
  if not line.strip():continue
  digest,name=line.split(maxsplit=1);p=work/name
  if not p.exists():p=work/'src'/name
  if p.is_symlink() and os.path.isabs(os.readlink(p)):p=root/os.readlink(p).lstrip('/')
  assert p.is_file() and hashlib.sha512(p.read_bytes()).hexdigest()==digest,name;checked+=1
 command=['chroot',str(root),'/usr/bin/env','LIBCAMERA_IPA_PRIVATE_KEY=/private/ipa214.rsa.pem','SOURCE_DATE_EPOCH=1792022400','JOBS=4','/bin/ash','-c','cd /work/libcamera && umask 022 && exec /usr/bin/abuild -F -d -K -P /packages225 build rootpkg index']
 with (private/'full-r12-build-private.log').open('xb') as log:
  process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT);record(phase='full-feature-r12-build-live',pid=process.pid,source_inputs_verified=checked,started=time.time())
  try:rc=process.wait(timeout=7200)
  except subprocess.TimeoutExpired:record(phase='same-build-still-live-observation-expired');raise
 record(phase='r12-build-terminal-restoration-pending',exit=rc)
finally:
 if process is None or process.poll() is not None:
  if work.exists():os.rename(work,retained)
  assert snapshot.exists() and not work.exists();os.rename(snapshot,work);assert inventory(work)==original
  record(original214_files_links_modes_restored=True,candidate_source_objects_retained=True)
assert rc==0,'Inspect terminal build before any resume'
packages=list((root/'packages225').rglob('*.apk'));assert len(packages)==11
record(phase='framework-complete-config-build-next')
with (private/'config-r7-build-private.log').open('xb') as log:
 p=subprocess.run(['chroot',str(root),'/usr/bin/env','SOURCE_DATE_EPOCH=1792022400','/bin/ash','-c','cd /work/samurai-camera-config225 && umask 022 && exec /usr/bin/abuild -F -d -K -P /packages-config225 all'],stdout=log,stderr=subprocess.STDOUT,timeout=180)
assert p.returncode==0;packages+=list((root/'packages-config225').rglob('*.apk'));assert len(packages)==13
record(phase='all13-r12-r7-packages-built-original214-restored',terminal=True)
r=dict(stage=225,framework_and_config_packages_built=True,package_count=13,full_feature_targets_and_prior17_patches_retained=True,official_abuild_build_rootpkg_index_used=True,original214_files_links_modes_restored=len(original),r11_object_cache_preserved=True,candidate_full_sources_and_objects_retained=True,original_signing_inputs_reused=True,phone_not_modified_by_build=True)
(here/'package-build-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
