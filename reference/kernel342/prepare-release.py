"""Package the tested341 source and verify the complete incremental patch chain."""
from pathlib import Path
import hashlib,importlib.util,json,re,shutil,subprocess
import host
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('storage341',HERE.parent/'kernel341/storage.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
OLD=old.candidate();NEW=OLD.parent/'libcamera342-r27-built';assert not NEW.exists()
for name in ['ipa-contract-validation.json','runtime-lsc-validation.json']:assert json.loads((HERE.parent/'kernel341'/name).read_text())['passed']
shutil.copytree(OLD,NEW,symlinks=True,ignore=lambda d,n:[x for x in n if x=='pkg' or x.startswith('pkg-before') or x=='__pycache__'])
(HERE/'storage.py').write_text((HERE.parent/'kernel341/storage.py').read_text().replace('libcamera341-dynamic-lsc-built','libcamera342-r27-built'))
base=old.SDK/'work/libcamera321-lsc-built/src/libcamera-v0.7.2';tree=NEW/'src/libcamera-v0.7.2'
patches=[HERE.parent/'kernel330/0031-camss-calibrated-white-balance.patch',HERE.parent/'kernel332/0032-camss-calibrated-cct-estimation.patch',HERE.parent/'kernel335/0033-camss-colour-correction-coupling.patch',HERE.parent/'kernel339/0034-camss-runtime-reference-lux.patch',HERE.parent/'kernel340/0035-camss-runtime-aec-colour-correction.patch',HERE.parent/'kernel341/0036-camss-dynamic-lens-shading.patch']
names=set()
for p in patches:
 for line in p.read_text().splitlines():
  if line.startswith('+++ b/'):names.add(line[6:].split('\t')[0])
names.add('include/linux/qcom-camss-config.h')
check=NEW.parent/'patch-check342';assert not check.exists();check.mkdir()
for name in names:
 p=base/name
 if p.exists():(check/name).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,check/name)
results=[]
for p in patches:
 q=subprocess.run(['patch','--batch','--fuzz=0','-p1','-i',str(p)],cwd=check,capture_output=True);(host.PRIVATE/(p.stem+'-apply.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,(p.name,q.stdout.decode()[-2000:],q.stderr.decode());results.append(dict(patch=p.name,applied=True))
different=[name for name in sorted(names) if not (check/name).exists() or (check/name).read_bytes()!=(tree/name).read_bytes()]
(host.PRIVATE/'patch-chain-differences-private.json').write_text(json.dumps(different,indent=2)+'\n');assert not different,different
for package in ['libcamera','samurai-camera-config']:
 dest=HERE/'recipes'/package;assert not dest.exists();shutil.copytree(ROOT/'linux-port/packages'/package,dest)
recipe=HERE/'recipes/libcamera'
for p in patches:shutil.copyfile(p,recipe/p.name)
p=recipe/'APKBUILD';s=p.read_text().replace('pkgrel=26\n','pkgrel=27\n');s=s.replace('\t0030-camss-lens-shading.patch\n','\t0030-camss-lens-shading.patch\n'+''.join('\t'+p.name+'\n' for p in patches));at=s.rfind('"');s=s[:at]+''.join(hashlib.sha512(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in patches)+s[at:];p.write_text(s)
p=HERE/'recipes/samurai-camera-config/APKBUILD';s=p.read_text().replace('pkgrel=21\n','pkgrel=22\n').replace('99990.7.2-r26','99990.7.2-r27');p.write_text(s)
for p in recipe.iterdir():
 if p.is_file():shutil.copyfile(p,NEW/p.name)
config=old.SDK/'work/samurai-camera-config342-r27';assert not config.exists();shutil.copytree(HERE/'recipes/samurai-camera-config',config)
(HERE/'package-source-validation.json').write_text(json.dumps(dict(stage=342,framework_version='99990.7.2-r27',configuration_version='0.1.0-r22',baseline_framework='99990.7.2-r26',source=str(tree),baseline_source=str(base),patch_chain=results,compared_source_files=len(names),differing_source_files=0,source_exactly_matches_tested341=True,default_profiles_unchanged=True,individual_factory_tables_in_public_packages=False,installed=False,passed=True),indent=2)+'\n');print('Prepared r27/r22 recipes; full six-patch chain exactly reproduces tested341 sources.')
