"""Resume a recipe-only copy after chroot-absolute source symlinks failed."""
from pathlib import Path
import hashlib,json,os,shutil
here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel224');sdk=Path('/home/cy122/x2pro-linux/libcamera214-root')
source=sdk/'work/samurai-camera-config224';config=sdk/'work/samurai-camera-config224-r10';retained=sdk/'private/config224-r10-partial-copy'
assert config.is_dir() and not retained.exists()
for p in [source,config,retained]:assert p.parent.resolve().is_relative_to(sdk.resolve()) and not p.is_symlink()
assert not (private/'r10-build-state-private.json').exists()
os.rename(config,retained);config.mkdir()
for name in ['APKBUILD','configuration.yaml','70-samurai-camera-heaps.rules','samurai-camera-heaps.conf','README.md']:
 assert (source/name).is_file() and not (source/name).is_symlink();shutil.copyfile(source/name,config/name)
apk=(config/'APKBUILD').read_text();assert apk.count('pkgrel=4')==1;apk=apk.replace('pkgrel=4','pkgrel=5').replace('99990.7.2-r9','99990.7.2-r10');(config/'APKBUILD').write_text(apk)
name='src/libcamera/pipeline/simple/simple.cpp';base=sdk/'work/libcamera224-built/src/libcamera-v0.7.2'/name;candidate=private/'stop-fix-source'/name;patch=here/'libcamera-stop-live-requests.patch'
proof=dict(stage=224,candidate_framework='99990.7.2-r10',candidate_config_stack='0.1.0-r5',patch_sha256=hashlib.sha256(patch.read_bytes()).hexdigest(),original_sources_sha256={name:hashlib.sha256(base.read_bytes()).hexdigest()},source_files={name:hashlib.sha256(candidate.read_bytes()).hexdigest()},stop_cleanup_uses_live_request_ownership=True,r9_failed_candidate_artifacts_and_evidence_preserved=True,phone_still_r8_r3=True,partial_config_copy_retained_privately=True,config_recipe_only_copy_avoids_chroot_absolute_build_symlinks=True)
(here/'stop-fix-source-validation.json').write_text(json.dumps(proof,indent=2)+'\n')
build=(here/'build-r9-candidate.py').read_text()
build=build.replace("snapshot=root/'private/libcamera214-before224'","snapshot=root/'private/libcamera214-before224-r10'").replace("retained=root/'work/libcamera224-built'","retained=root/'work/libcamera224-r10-built'").replace("cache=root/'work/libcamera223-built'","cache=root/'work/libcamera224-built'").replace("recipe=root/'work/libcamera224'","recipe=root/'work/libcamera224-r10'")
build=build.replace('packages224','packages224-r10').replace('packages-config224','packages-config224-r10').replace('samurai-camera-config224','samurai-camera-config224-r10').replace('r9','r10').replace('r4','r5').replace('r8_object_cache_preserved','r9_object_cache_preserved').replace('prior14','prior15').replace('0015-simple-raw-only-statistics.patch','0016-simple-stop-live-requests.patch').replace("here/'candidate-source-validation.json'","here/'stop-fix-source-validation.json'").replace("here/'package-build-validation.json'","here/'r10-package-build-validation.json'")
compile(build,'full-r10-build224','exec');(here/'build-r10-candidate.py').write_text(build)
print(json.dumps(proof))
