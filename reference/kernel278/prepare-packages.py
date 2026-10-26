"""Retain the full framework; put the model/lens profile in the device data package."""
from pathlib import Path
import hashlib,json,shutil
import host
R=Path(__file__).resolve().parent;W=R.parents[1];SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
proof=json.loads((R/'af-source-validation.json').read_text());patch=R/'0028-simple-contrast-autofocus.patch';assert proof['patch_count']==28
for name in ['libcamera','samurai-camera-config']:
 out=R/'recipes'/name;out.mkdir(parents=True)
 for p in (W/'linux-port/packages'/name).iterdir():
  if p.is_file() and p.name not in ['README.md','source-lock.json']:shutil.copyfile(p,out/p.name)
recipe=R/'recipes/libcamera';shutil.copyfile(patch,recipe/patch.name)
p=recipe/'APKBUILD';text=p.read_text();assert text.count('pkgrel=23\n')==1;text=text.replace('pkgrel=23\n','pkgrel=24\n')
needle='\t0027-softisp-raw-focus-statistics.patch\n';assert text.count(needle)==1;text=text.replace(needle,needle+'\t'+patch.name+'\n');end=text.rfind('"')
text=text[:end]+hashlib.sha512(patch.read_bytes()).hexdigest()+'  '+patch.name+'\n'+text[end:];p.write_text(text)
device=R/'recipes/samurai-camera-config';shutil.copyfile(R/'s5kgw1.yaml',device/'s5kgw1.yaml')
p=device/'APKBUILD';text=p.read_text();assert text.count('pkgrel=18\n')==1;text=text.replace('pkgrel=18\n','pkgrel=19\n').replace('99990.7.2-r23','99990.7.2-r24')
old='source="configuration.yaml samurai-camera-heaps.conf 70-samurai-camera-heaps.rules"';assert old in text;text=text.replace(old,old[:-1]+' s5kgw1.yaml"')
old='package() {\n';assert text.count(old)==1;text=text.replace(old,old+'\tinstall -Dm644 "$srcdir"/s5kgw1.yaml "$pkgdir"/usr/share/libcamera/ipa/simple/s5kgw1.yaml\n')
end=text.rfind('"');text=text[:end]+hashlib.sha512((device/'s5kgw1.yaml').read_bytes()).hexdigest()+'  s5kgw1.yaml\n'+text[end:];p.write_text(text)
for src,dest in [(recipe,SDK/'work/libcamera278-r24'),(device,SDK/'work/samurai-camera-config278-r24')]:
 assert not dest.exists();shutil.copytree(src,dest)
proof.update(framework_version='99990.7.2-r24',config_version='0.1.0-r19',prior27_patches_retained=True,profile_only_in_device_data_package=True,phone_unchanged=True)
(R/'package-source-validation.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(dict(stage=278,framework=proof['framework_version'],config=proof['config_version'])))
