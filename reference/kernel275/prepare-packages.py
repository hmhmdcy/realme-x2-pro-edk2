"""Retain full framework features; prepare a separate r22/r17 candidate recipe."""
from pathlib import Path
import hashlib,json,shutil
import host
R=Path(__file__).resolve().parent;W=R.parents[1];SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
proof=json.loads((R/'lifecycle-source-validation.json').read_text());patch=R/'0026-simple-lens-stream-lifetime.patch'
assert proof['patch_count']==26
for name in ['libcamera','samurai-camera-config']:
 out=R/'recipes'/name;out.mkdir(parents=True)
 for p in (W/'linux-port/packages'/name).iterdir():
  if p.is_file() and p.name not in ['README.md','source-lock.json']:shutil.copyfile(p,out/p.name)
recipe=R/'recipes/libcamera';shutil.copyfile(patch,recipe/patch.name)
p=recipe/'APKBUILD';text=p.read_text();assert text.count('pkgrel=21\n')==1;text=text.replace('pkgrel=21\n','pkgrel=22\n')
needle='\t0025-s5kgw1-native-gain-helper.patch\n';assert text.count(needle)==1;text=text.replace(needle,needle+'\t'+patch.name+'\n');end=text.rfind('"')
text=text[:end]+hashlib.sha512(patch.read_bytes()).hexdigest()+'  '+patch.name+'\n'+text[end:];p.write_text(text)
p=R/'recipes/samurai-camera-config/APKBUILD';text=p.read_text();assert text.count('pkgrel=16\n')==1;p.write_text(text.replace('pkgrel=16\n','pkgrel=17\n').replace('99990.7.2-r21','99990.7.2-r22'))
for src,dest in [(recipe,SDK/'work/libcamera275-r22'),(R/'recipes/samurai-camera-config',SDK/'work/samurai-camera-config275-r22')]:
 assert not dest.exists();shutil.copytree(src,dest)
proof.update(framework_version='99990.7.2-r22',config_version='0.1.0-r17',prior25_patches_retained=True,no_af_tuning_or_kernel_controls_changed=True,phone_unchanged=True)
(R/'package-source-validation.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(dict(stage=275,patch_count=26,framework=proof['framework_version'],config=proof['config_version']),indent=2))
