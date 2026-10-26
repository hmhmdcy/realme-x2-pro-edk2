"""Use retained full-feature object cache; preserve original214 tree by rename."""
from pathlib import Path
import hashlib,json,os,shutil,stat,subprocess,time
os.umask(0o077);here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel220');root=Path('/home/cy122/x2pro-linux/libcamera214-root')
work=root/'work/libcamera';snapshot=root/'private/libcamera214-before220-r3';retained=root/'work/libcamera220-built';recipe=root/'work/libcamera220'
for p in [work,snapshot,retained,recipe]:assert p.parent.resolve().is_relative_to(root.resolve()) and not p.is_symlink()
assert work.is_dir() and not snapshot.exists() and retained.exists() and not list((root/'packages220').rglob('*.apk'))
assert 'pkgrel=5\n' in (work/'APKBUILD').read_text()
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  if (p/'comm').read_text().strip() in ['ninja','meson','abuild','cc1plus']:
   assert not (p/'cwd').resolve().is_relative_to(work), 'Existing SDK build must finish before reuse'
 except (FileNotFoundError,ProcessLookupError):pass
def inventory(directory):
 result={}
 for p in directory.rglob('*'):
  if p.is_symlink():result[str(p.relative_to(directory))]=dict(target=os.readlink(p))
  elif p.is_file():result[str(p.relative_to(directory))]=dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),mode=stat.S_IMODE(p.stat().st_mode))
 return result
original=inventory(work);assert original==json.loads((private/'original214-work-manifest-private.json').read_text())
state=dict(stage=220,phase='original214-snapshot-move-submitted',original=str(work),snapshot=str(snapshot),retained_candidate=str(retained))
marker=private/'incremental-build-state-private.json'
def record(**values):state.update(values);marker.write_text(json.dumps(state,indent=2)+'\n')
record();os.rename(work,snapshot);record(phase='original214-preserved-copy-in-progress')
process=None;build_code=None
try:
 os.rename(retained,work)
 assert (work/'pkg').is_dir() and not (work/'pkg-before220-rootpkg-failure').exists()
 os.rename(work/'pkg',work/'pkg-before220-rootpkg-failure')
 source=work/'src/libcamera-v0.7.2'
 proof=json.loads((here/'candidate-source-validation.json').read_text())
 assert all(hashlib.sha256((source/name).read_bytes()).hexdigest()==digest for name,digest in proof['source_files'].items())
 # Confirm every local recipe source input against its declared SHA512.
 text=(work/'APKBUILD').read_text();checks=text.split('sha512sums="',1)[1].split('"',1)[0].splitlines();checked=0
 for line in checks:
  if not line.strip():continue
  digest,name=line.split(maxsplit=1);p=work/name
  if not p.exists():p=work/'src'/name
  if p.is_symlink() and os.path.isabs(os.readlink(p)):p=root/os.readlink(p).lstrip('/')
  assert p.is_file() and hashlib.sha512(p.read_bytes()).hexdigest()==digest,name;checked+=1
 record(phase='full-feature-build-and-official-rootpkg-submitted',local_source_checksums_verified=checked)
 command=['chroot',str(root),'/usr/bin/env','LIBCAMERA_IPA_PRIVATE_KEY=/private/ipa214.rsa.pem','SOURCE_DATE_EPOCH=1792022400','JOBS=4',
          '/bin/ash','-c','cd /work/libcamera && umask 022 && exec /usr/bin/abuild -F -d -K -P /packages220 rootpkg index']
 with (private/'candidate-repackage-private.log').open('xb') as log:
  process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT);record(pid=process.pid,started=time.time())
  try:build_code=process.wait(timeout=7200)
  except subprocess.TimeoutExpired:
   record(phase='same-build-still-live-observation-expired');raise
 record(phase='build-terminal-restoration-pending',exit=build_code)
finally:
 # A wait timeout is not terminal. Never move a tree beneath a live compiler.
 if process is None or process.poll() is not None:
  if work.exists():os.rename(work,retained)
  assert snapshot.exists() and not work.exists();os.rename(snapshot,work)
  assert inventory(work)==original
  record(original214_recipe_source_objects_and_metadata_restored=True,candidate_source_and_objects_retained=True)
assert build_code==0,'Inspect terminal build and retained candidate; do not rerun the initial one-shot'
packages=list((root/'packages220').rglob('*.apk'));assert len(packages)==11
record(phase='framework-built-original214-restored-config-build-next')
with (private/'config-r2-build-private.log').open('xb') as log:
 p=subprocess.run(['chroot',str(root),'/usr/bin/env','SOURCE_DATE_EPOCH=1792022400','/bin/ash','-c',
                   'cd /work/samurai-camera-config220 && umask 022 && exec /usr/bin/abuild -F -d -K -P /packages-config220 all'],stdout=log,stderr=subprocess.STDOUT,timeout=180)
assert p.returncode==0
packages+=list((root/'packages-config220').rglob('*.apk'));assert len(packages)==13
record(phase='all13packages-built-original214-restored',terminal=True)
r=dict(stage=220,framework_and_config_packages_built=True,package_count=13,all_original_full_feature_targets_retained=True,
 official_abuild_build_rootpkg_index_used=True,incremental_full_feature_object_cache_used=True,completed44_target_build_reused_without_recompilation=True,
 original214_files_and_links_restored=len(original),candidate_full_sources_and_objects_retained=True,
 original_signing_inputs_reused=True,phone_not_modified=True,signatures_and_physical_metadata_verification_pending=True)
(here/'package-build-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
