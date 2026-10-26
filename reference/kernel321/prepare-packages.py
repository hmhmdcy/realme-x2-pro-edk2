from pathlib import Path
import difflib,hashlib,json,shutil
import host
HERE=Path(__file__).resolve().parent;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
BASE=SDK/'work/libcamera316-r25-built/src/libcamera-v0.7.2';NEW=SDK/'work/libcamera321-lsc-built/src/libcamera-v0.7.2'
assert json.loads((HERE/'native-r2-image-validation.json').read_text())['passed']
names=['include/linux/qcom-camss-config.h']
for folder,path in [('ipa','src/ipa/camss-vfe'),('libipa','src/ipa/libipa')]:
 names += [path+'/'+p.name for p in (HERE/folder).iterdir() if p.is_file()]
patch=[]
for name in names:
 before=(BASE/name).read_text() if (BASE/name).exists() else ''
 after=(NEW/name).read_text()
 patch.extend(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+name if before else '/dev/null',tofile='b/'+name))
name='0030-camss-lens-shading.patch';(HERE/name).write_text(''.join(patch))
for package in ['libcamera','samurai-camera-config']:
 dest=HERE/'recipes'/package;assert not dest.exists();shutil.copytree(HERE.parent/'kernel316/recipes'/package,dest)
lib=HERE/'recipes/libcamera';shutil.copyfile(HERE/name,lib/name)
p=lib/'APKBUILD';s=p.read_text().replace('pkgrel=25\n','pkgrel=26\n')
s=s.replace('\t0029-camss-hardware-pipeline.patch\n','\t0029-camss-hardware-pipeline.patch\n\t'+name+'\n')
at=s.rfind('"');s=s[:at]+hashlib.sha512((HERE/name).read_bytes()).hexdigest()+'  '+name+'\n'+s[at:];p.write_text(s)
p=HERE/'recipes/samurai-camera-config/APKBUILD';s=p.read_text().replace('pkgrel=20\n','pkgrel=21\n').replace('99990.7.2-r25','99990.7.2-r26');p.write_text(s)
for package,dest in [('libcamera',SDK/'work/libcamera321-r26'),('samurai-camera-config',SDK/'work/samurai-camera-config321-r26')]:
 assert not dest.exists();shutil.copytree(HERE/'recipes'/package,dest)
(HERE/'package-source-validation.json').write_text(json.dumps(dict(stage=321,framework_version='99990.7.2-r26',configuration_version='0.1.0-r21',incremental_patch=name,changed_sources=names,
 base_recipe_stage=316,default_profiles_unchanged=True,individual_values_in_packages=False,installed=False),indent=2)+'\n')
s=(HERE.parent/'kernel316/collect-packages.py').read_text().replace('packages316-r25','packages321-r26').replace('packages-config316-r25','packages-config321-r26').replace('candidate316-r25','candidate321-r26').replace('libcamera316-r25-built','libcamera321-lsc-built').replace('stage=316','stage=321').replace('CAMSS316','CAMSS321').replace('99990.7.2-r25','99990.7.2-r26').replace('0.1.0-r20','0.1.0-r21')
a=s.index('baseline=json.loads(');b=s.index('for kind in ',a)
s=s[:a]+'''rollback=repository/'rollback';rollback.mkdir(exist_ok=True)
for p in (host.PRIVATE.parent/'kernel316/runtime-repository/forward').glob('*.apk'):
 shutil.copyfile(p,rollback/p.name)
'''+s[b:]
(HERE/'collect-packages.py').write_text(s)
print('Prepared r26/r21 recipes; default tuning and kernel remain unchanged.')
