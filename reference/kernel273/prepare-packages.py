"""Create r21/r16 recipes for the tested GW1 helper, keeping deployed r20 intact."""
from pathlib import Path
import hashlib,json,shutil
import host
R=Path(__file__).resolve().parent;W=R.parents[1];SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
proof=json.loads((R.parent/'kernel272/helper-candidate-validation.json').read_text())
assert proof['results']['candidate']['report']['native_codes_round_tripped']==993
patch=R.parent/'kernel272/0025-s5kgw1-native-gain-helper.patch';assert hashlib.sha256(patch.read_bytes()).hexdigest()==proof['patch_sha256']
for name in ['libcamera','samurai-camera-config']:
 out=R/'recipes'/name;out.mkdir(parents=True)
 for p in (W/'linux-port/packages'/name).iterdir():
  if p.is_file() and p.name not in ['README.md','source-lock.json']:shutil.copyfile(p,out/p.name)
recipe=R/'recipes/libcamera';shutil.copyfile(patch,recipe/patch.name)
p=recipe/'APKBUILD';text=p.read_text();assert text.count('pkgrel=20\n')==1
text=text.replace('pkgrel=20\n','pkgrel=21\n')
needle='\t0024-s5k3m5-native-gain-helper.patch\n';assert text.count(needle)==1
text=text.replace(needle,needle+'\t'+patch.name+'\n');end=text.rfind('"')
text=text[:end]+hashlib.sha512(patch.read_bytes()).hexdigest()+'  '+patch.name+'\n'+text[end:];p.write_text(text)
p=R/'recipes/samurai-camera-config/APKBUILD';text=p.read_text();assert text.count('pkgrel=15\n')==1
p.write_text(text.replace('pkgrel=15\n','pkgrel=16\n').replace('99990.7.2-r20','99990.7.2-r21'))
for src,dest in [(recipe,SDK/'work/libcamera273-r21'),(R/'recipes/samurai-camera-config',SDK/'work/samurai-camera-config273-r21')]:
 assert not dest.exists();shutil.copytree(src,dest)
report=dict(stage=273,patch_count=25,source_before_files={'src/ipa/libipa/camera_sensor_helper.cpp':proof['source_before_sha256']},
 source_files={'src/ipa/libipa/camera_sensor_helper.cpp':proof['source_after_sha256']},
 framework_version='99990.7.2-r21',config_version='0.1.0-r16',prior24_patches_retained=True,
 no_tuning_blacklevel_or_delay_changes=True,phone_unchanged=True)
(R/'package-source-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
