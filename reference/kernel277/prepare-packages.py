"""Prepare full r23/r18 recipes separately, leaving the deployed r22 stack alone."""
from pathlib import Path
import hashlib,json,shutil
import host
R=Path(__file__).resolve().parent;W=R.parents[1];SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
proof=json.loads((R/'focus-source-validation.json').read_text());patch=R/'0027-softisp-raw-focus-statistics.patch'
assert proof['patch_count']==27
for name in ['libcamera','samurai-camera-config']:
 out=R/'recipes'/name;out.mkdir(parents=True)
 for p in (W/'linux-port/packages'/name).iterdir():
  if p.is_file() and p.name not in ['README.md','source-lock.json']:shutil.copyfile(p,out/p.name)
recipe=R/'recipes/libcamera';shutil.copyfile(patch,recipe/patch.name)
p=recipe/'APKBUILD';text=p.read_text();assert text.count('pkgrel=22\n')==1;text=text.replace('pkgrel=22\n','pkgrel=23\n')
needle='\t0026-simple-lens-stream-lifetime.patch\n';assert text.count(needle)==1;text=text.replace(needle,needle+'\t'+patch.name+'\n');end=text.rfind('"')
text=text[:end]+hashlib.sha512(patch.read_bytes()).hexdigest()+'  '+patch.name+'\n'+text[end:];p.write_text(text)
p=R/'recipes/samurai-camera-config/APKBUILD';text=p.read_text();assert text.count('pkgrel=17\n')==1;p.write_text(text.replace('pkgrel=17\n','pkgrel=18\n').replace('99990.7.2-r22','99990.7.2-r23'))
for src,dest in [(recipe,SDK/'work/libcamera277-r23'),(R/'recipes/samurai-camera-config',SDK/'work/samurai-camera-config277-r23')]:
 assert not dest.exists();shutil.copytree(src,dest)
proof.update(framework_version='99990.7.2-r23',config_version='0.1.0-r18',prior26_patches_retained=True,phone_unchanged=True)
(R/'package-source-validation.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(dict(stage=277,framework=proof['framework_version'],config=proof['config_version'])))
