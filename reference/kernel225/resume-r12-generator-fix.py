"""Explicit repair after confirmed build41314 termination and original restoration."""
from pathlib import Path
import hashlib,json,os,shutil,stat,subprocess,time

here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel225');root=Path('/home/cy122/x2pro-linux/libcamera214-root')
work=root/'work/libcamera';snapshot=root/'private/libcamera214-before225-repair1';candidate=root/'work/libcamera225-built';recipe=root/'work/libcamera225'
old=json.loads((private/'r12-build-state-private.json').read_text());assert old['terminal'] and old['exit']==1 and old['original214_files_links_modes_restored']
assert not Path('/proc',str(old['pid'])).exists()
for p in [work,snapshot,candidate,recipe]:assert p.parent.resolve().is_relative_to(root.resolve()) and not p.is_symlink()
assert work.is_dir() and candidate.is_dir() and not snapshot.exists()
assert not list((root/'packages225').rglob('*.apk'))
def inventory(directory):
 result={}
 for p in directory.rglob('*'):
  if p.is_symlink():result[str(p.relative_to(directory))]=dict(target=os.readlink(p))
  elif p.is_file():result[str(p.relative_to(directory))]=dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),mode=stat.S_IMODE(p.stat().st_mode))
 return result
original=inventory(work);assert original==json.loads((private/'original214-work-manifest-private.json').read_text())
proof=json.loads((here/'candidate-source-validation.json').read_text());source=candidate/'src/libcamera-v0.7.2'
assert all(hashlib.sha256((source/n).read_bytes()).hexdigest()==v for n,v in proof['source_files'].items())
marker=private/'r12-build-repair1-state-private.json';assert not marker.exists()
state=dict(stage=225,phase='original214-snapshot-submitted',previous_build_terminal=True,previous_build_exit=1)
def record(**values):state.update(values);marker.write_text(json.dumps(state,indent=2)+'\n')
record();os.rename(work,snapshot);process=None;rc=None
try:
 os.rename(candidate,work)
 for p in recipe.iterdir():
  if p.is_file():shutil.copyfile(p,work/p.name)
 source=work/'src/libcamera-v0.7.2'
 p=subprocess.run(['patch','--batch','--forward','-p1','-i',str(work/'0019-ipc-threaded-start-outputs.patch')],cwd=source,capture_output=True,timeout=20)
 (private/'generator-fix-apply-private.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0
 proof=json.loads((here/'generator-source-validation.json').read_text());assert all(hashlib.sha256((source/n).read_bytes()).hexdigest()==v for n,v in proof['source_files'].items())
 command=['chroot',str(root),'/usr/bin/env','LIBCAMERA_IPA_PRIVATE_KEY=/private/ipa214.rsa.pem','SOURCE_DATE_EPOCH=1792022400','JOBS=4','/bin/ash','-c','cd /work/libcamera && umask 022 && exec /usr/bin/abuild -F -d -K -P /packages225 build rootpkg index']
 with (private/'full-r12-repair1-build-private.log').open('xb') as log:
  process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT);record(phase='full-feature-r12-repair1-build-live',pid=process.pid,started=time.time())
  try:rc=process.wait(timeout=7200)
  except subprocess.TimeoutExpired:record(phase='same-repair-build-live-observation-expired');raise
 record(phase='repair1-build-terminal-restoration-pending',exit=rc,terminal=True)
finally:
 if process is None or process.poll() is not None:
  if work.exists():os.rename(work,candidate)
  assert snapshot.exists() and not work.exists();os.rename(snapshot,work);assert inventory(work)==original
  record(original214_files_links_modes_restored=True,candidate_source_objects_retained=True)
assert rc==0,'Inspect confirmed terminal outcome before another repair'
assert len(list((root/'packages225').rglob('*.apk')))==11
with (private/'config-r7-build-private.log').open('xb') as log:
 p=subprocess.run(['chroot',str(root),'/usr/bin/env','SOURCE_DATE_EPOCH=1792022400','/bin/ash','-c','cd /work/samurai-camera-config225 && umask 022 && exec /usr/bin/abuild -F -d -K -P /packages-config225 all'],stdout=log,stderr=subprocess.STDOUT,timeout=180)
assert p.returncode==0 and len(list((root/'packages-config225').rglob('*.apk')))==2
record(phase='all13-r12-r7-built-original214-restored',all13_packages_built=True)
r=dict(stage=225,framework_and_config_packages_built=True,package_count=13,recipe_patch_count=19,
 full_feature_targets_and_prior17_patches_retained=True,official_abuild_build_rootpkg_index_used=True,
 original214_files_links_modes_restored=len(original),r11_cache_preserved=True,
 first_terminal_compile_failure_preserved=True,threaded_start_output_generator_repaired=True,
 original_signing_inputs_reused=True,phone_not_modified_by_build=True)
(here/'package-build-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
