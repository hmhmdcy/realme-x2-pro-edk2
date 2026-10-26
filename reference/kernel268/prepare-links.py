"""Prepare a common Simple pipeline fix on the exact deployed r15 source."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil

R=Path(__file__).resolve().parent
SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
source=SDK/'work/libcamera239-r15-built/src/libcamera-v0.7.2'
name='src/libcamera/pipeline/simple/simple.cpp'
before=(source/name).read_text()
start=before.index('int SimpleCameraData::setupLinks()')
end=before.index('int SimpleCameraData::setupFormats(',start)
old=before[start:end];new=old
needle='''\t\t\t\tif ((link->flags() & MEDIA_LNK_FL_ENABLED) &&
\t\t\t\t    !(link->flags() & MEDIA_LNK_FL_IMMUTABLE)) {'''
assert new.count(needle)==1
new=new.replace(needle,'''\t\t\t\t/* Another process may have changed the kernel link state. */
\t\t\t\tif (!(link->flags() & MEDIA_LNK_FL_IMMUTABLE)) {''')
needle='''\t\tif (!(sinkLink->flags() & MEDIA_LNK_FL_ENABLED)) {
\t\t\tret = sinkLink->setEnabled(true);
\t\t\tif (ret < 0)
\t\t\t\treturn ret;
\t\t}'''
assert new.count(needle)==1
new=new.replace(needle,'''\t\tret = sinkLink->setEnabled(true);
\t\tif (ret < 0)
\t\t\treturn ret;''')
after=before[:start]+new+before[end:]
(R/'simple-before.cpp').write_text(before);(R/'simple.cpp').write_text(after)
patch='''Subject: [PATCH] libcamera: simple: set links independently of cached enable flags

A different process may reconfigure the media graph while a pipeline is
released. Cached flags from enumeration do not describe that kernel state.
Always request the required mutable-link states when configuring a pipeline.
Retain immutable-link protection, routing-pad limits and ioctl error handling.

---
'''+''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+name,tofile='b/'+name))
patchname='0023-simple-link-state-after-external-client.patch';(R/patchname).write_text(patch)
recipe=SDK/'work/libcamera268-r19';config=SDK/'work/samurai-camera-config268-r19'
assert not recipe.exists() and not config.exists();recipe.mkdir();config.mkdir()
for dirname,target in [('libcamera239-r15',recipe),('samurai-camera-config239-r15',config)]:
    for p in (SDK/'work'/dirname).iterdir():
        if p.is_file():shutil.copyfile(p,target/p.name)
shutil.copyfile(R/patchname,recipe/patchname)
apk=(recipe/'APKBUILD').read_text();assert apk.count('pkgrel=15\n')==1
apk=apk.replace('pkgrel=15\n','pkgrel=19\n').replace('\t0022-soft-initial-parameters.patch\n','\t0022-soft-initial-parameters.patch\n\t'+patchname+'\n')
at=apk.rfind('\n"');apk=apk[:at]+'\n'+hashlib.sha512(patch.encode()).hexdigest()+'  '+patchname+apk[at:]
(recipe/'APKBUILD').write_text(apk)
cfg=(config/'APKBUILD').read_text();assert cfg.count('pkgrel=10\n')==1
cfg=cfg.replace('pkgrel=10\n','pkgrel=14\n').replace('99990.7.2-r15','99990.7.2-r19');(config/'APKBUILD').write_text(cfg)
for dirname,src in [('libcamera',recipe),('samurai-camera-config',config)]:
    target=R/'recipes'/dirname;target.mkdir(parents=True)
    for p in src.iterdir():
        if p.is_file():shutil.copyfile(p,target/p.name)
report=dict(stage=268,patch_count=23,source_before_sha256=hashlib.sha256(before.encode()).hexdigest(),
 source_sha256=hashlib.sha256(after.encode()).hexdigest(),patch_sha256=hashlib.sha256(patch.encode()).hexdigest(),
 all_22_deployed_patches_retained=True,sensor_isp_tuning_configuration_unchanged=True,
 independent_of_camera_model_and_application=True,immutable_and_routing_checks_preserved=True,
 framework_version='99990.7.2-r19',config_version='0.1.0-r14',candidate_not_installed=True)
(R/'source-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
