from pathlib import Path
import difflib,hashlib,json,re,shutil

here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel225');sdk=Path('/home/cy122/x2pro-linux/libcamera214-root')
test=json.loads((here/'agc-preflight-validation.json').read_text());assert test['run_exit']==1 and test['failed_latest_target_hold_requirement']
assert json.loads((private/'r12-build-repair1-state-private.json').read_text())['all13_packages_built']
assert not list((sdk/'private').glob('libcamera214-before225*'))
name='src/ipa/simple/algorithms/agc.cpp';base=sdk/'work/libcamera225-built/src/libcamera-v0.7.2';original=(base/name).read_text();text=original
for old in ['if (!frameContext.agc.autoExposure || !sourcesMatch)','if (!frameContext.agc.autoGain || !sourcesMatch)']:
 assert text.count(old)==1;text=text.replace(old,old[:-1]+' || !stats->valid)')
patch='''Subject: [PATCH] soft: preserve computed targets when statistics are invalid

An invalid statistics frame may still contain an older captured exposure
and gain. Keep the latest prepared automatic targets in that case, instead
of scheduling the older captured values again. Metadata continues to
describe the actual captured controls and their source.

---
diff --git a/'''+name+' b/'+name+'\n'+''.join(difflib.unified_diff(original.splitlines(True),text.splitlines(True),fromfile='a/'+name,tofile='b/'+name))
(here/'libcamera-invalid-statistics-hold.patch').write_text(patch)
p=private/'statistics-hold-source'/name;assert not p.exists();p.parent.mkdir(parents=True);p.write_text(text)
recipe=sdk/'work/libcamera225-r13';assert not recipe.exists();recipe.mkdir()
for p in (sdk/'work/libcamera225').iterdir():
 if p.is_file() and not p.is_symlink():shutil.copyfile(p,recipe/p.name)
patchname='0020-soft-invalid-statistics-hold.patch';(recipe/patchname).write_text(patch)
apk=(recipe/'APKBUILD').read_text();assert apk.count('pkgrel=12\n')==1;apk=apk.replace('pkgrel=12\n','pkgrel=13\n')
marker='\t0019-ipc-threaded-start-outputs.patch\n';assert apk.count(marker)==1;apk=apk.replace(marker,marker+'\t'+patchname+'\n')
marker=next(l for l in apk.splitlines(True) if l.rstrip().endswith('  0019-ipc-threaded-start-outputs.patch'));apk=apk.replace(marker,marker+hashlib.sha512(patch.encode()).hexdigest()+'  '+patchname+'\n');(recipe/'APKBUILD').write_text(apk)
config=sdk/'work/samurai-camera-config225-r13';assert not config.exists();config.mkdir()
for name in ['APKBUILD','configuration.yaml','70-samurai-camera-heaps.rules','samurai-camera-heaps.conf','README.md']:shutil.copyfile(sdk/'work/samurai-camera-config225'/name,config/name)
apk=(config/'APKBUILD').read_text().replace('pkgrel=7\n','pkgrel=8\n').replace('99990.7.2-r12','99990.7.2-r13');(config/'APKBUILD').write_text(apk)
proof=dict(stage=225,candidate_framework='99990.7.2-r13',candidate_config_stack='0.1.0-r8',
 patch_sha256=hashlib.sha256(patch.encode()).hexdigest(),original_sources_sha256={name:hashlib.sha256(original.encode()).hexdigest()},
 source_files={name:hashlib.sha256(text.encode()).hexdigest()},
 r12_full_packages_and_failed_behavioral_test_retained=True,invalid_statistics_uses_latest_target_not_older_capture=True,phone_still_r11_r6=True)
# The source filename must not be the later configuration-copy loop variable.
source_name='src/ipa/simple/algorithms/agc.cpp'
proof['original_sources_sha256']={source_name:hashlib.sha256(original.encode()).hexdigest()}
proof['source_files']={source_name:hashlib.sha256(text.encode()).hexdigest()}
(here/'statistics-hold-source-validation.json').write_text(json.dumps(proof,indent=2)+'\n')
build=(here.parent/'kernel224/build-r11-candidate.py').read_text()
replacements={'kernel224':'kernel225','libcamera214-before224-r11':'libcamera214-before225-r13',
 'libcamera224-r11-built':'libcamera225-r13-built','libcamera224-r10-built':'libcamera225-built','libcamera224-r11':'libcamera225-r13',
 'packages224-r11':'packages225-r13','packages-config224-r11':'packages-config225-r13',
 'samurai-camera-config224-r11':'samurai-camera-config225-r13','r11-build-state-private.json':'r13-build-state-private.json',
 'r11-patch-apply-private.log':'r13-patch-apply-private.log','full-r11-build-private.log':'full-r13-build-private.log',
 'config-r6-build-private.log':'config-r8-build-private.log','r11-package-build-validation.json':'r13-package-build-validation.json',
 '0017-simple-capture-cancel-status.patch':patchname,'cancel-status-source-validation.json':'statistics-hold-source-validation.json',
 'stage=224':'stage=225','prior16':'prior19','r10_object_cache_preserved':'r12_object_cache_preserved',
 'retained-r10-cache-copy-live':'retained-r12-cache-copy-live','full-feature-r11-build-live':'full-feature-r13-build-live',
 'r11-build-terminal-restoration-pending':'r13-build-terminal-restoration-pending',
 'all13-r11-r6-packages-built-original214-restored':'all13-r13-r8-packages-built-original214-restored'}
pattern=re.compile('|'.join(re.escape(k) for k in sorted(replacements,key=len,reverse=True)));build=pattern.sub(lambda m:replacements[m.group()],build)
assert "cache=root/'work/libcamera225-built'" in build
compile(build,'build-r13-candidate.py','exec');(here/'build-r13-candidate.py').write_text(build)
print(json.dumps(dict(stage=225,new_candidate='r13/r8',r12_failed_requirement_preserved=True,patch_sha256=proof['patch_sha256'],not_deployed=True)))
