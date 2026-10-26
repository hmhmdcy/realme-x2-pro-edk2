"""Check the complete recipe queue against the exact pristine source archive."""
from pathlib import Path
import difflib,hashlib,json,re,subprocess,tarfile
R=Path(__file__).parent;repo=R.parents[1];recipe=repo/'linux-port/packages/pipewire-common'
private=Path('/mnt/e/edk2-samurai-out/kernel264');work=Path('/home/cy122/x2pro-linux/pipewire264-recipe-qa')
work.mkdir(exist_ok=True)
p=recipe/'APKBUILD';before=p.read_text()
original=work/'APKBUILD'
if not original.exists():
 original.write_text(before)
 q=subprocess.run(['patch','-R','-p3','-d',str(work)],input=(R/'upstream-recipe-overlay.patch').read_bytes(),capture_output=True)
 assert q.returncode==0,(q.stdout+q.stderr).decode()
assert hashlib.sha256(original.read_bytes()).hexdigest()=='09f9941b7f06c4c22fa8258b9beed39be39181250dddec882d3d75ac2cfcbac9'
url='https://github.com/PipeWire/pipewire/archive/refs/tags/$pkgver.tar.gz'
assert before.count(url)==1
after=before if 'pipewire-$pkgver.tar.gz::'+url in before else before.replace(url,'pipewire-$pkgver.tar.gz::'+url)
p.write_text(after)
generator=R/'prepare-recipe.py';s=generator.read_text()
if "s.replace(old_url,'"+url+"')" in s:generator.write_text(s.replace("s.replace(old_url,'"+url+"')","s.replace(old_url,'pipewire-$pkgver.tar.gz::"+url+"')"))
(R/'upstream-recipe-overlay.patch').write_text(''.join(difflib.unified_diff(original.read_text().splitlines(True),after.splitlines(True),fromfile='a/community/pipewire/APKBUILD',tofile='b/community/pipewire/APKBUILD')))
archive=Path('/mnt/e/edk2-samurai-out/kernel262/source/pipewire-1.6.9.tar.gz')
lock=json.loads((recipe/'source-lock.json').read_text());assert hashlib.sha256(archive.read_bytes()).hexdigest()==lock['source_tar']['sha256']
checks=re.findall(r'^([0-9a-f]{128})  (\S+)$',after,re.M);assert len(checks)==10
for digest,name in checks:
 data=(archive if name=='pipewire-1.6.9.tar.gz' else recipe/name).read_bytes()
 assert hashlib.sha512(data).hexdigest()==digest,name
assert not (work/'pipewire-1.6.9').exists()
with tarfile.open(archive) as a:
 for m in a:
  assert (m.name=='pipewire-1.6.9' or m.name.startswith('pipewire-1.6.9/')) and '..' not in Path(m.name).parts
 a.extractall(work,filter='data')
source=work/'pipewire-1.6.9';queue=['systemd-units-wo-libsystemd.patch']+list(lock['patch_sha256'])
logs=[]
for name in queue:
 q=subprocess.run(['patch','--batch','--fuzz=0','-p1','-d',str(source)],input=(recipe/name).read_bytes(),capture_output=True)
 logs.append(q.stdout+q.stderr);assert q.returncode==0,(name,(q.stdout+q.stderr).decode())
(private/'recipe-prepare-private.log').write_bytes(b'\n'.join(logs))
expected={'src/pipewire/impl-port.c':json.loads((R/'binding-reset-build-validation.json').read_text())['source_sha256'],'spa/plugins/libcamera/libcamera-source.cpp':json.loads((R/'reset-output-build-validation.json').read_text())['source_sha256']}
for name,digest in expected.items():assert hashlib.sha256((source/name).read_bytes()).hexdigest()==digest,name
syntax=subprocess.run(['sh','-n',str(p)],capture_output=True);assert syntax.returncode==0,syntax.stderr
report=dict(stage=264,pristine_archive_sha256_verified=True,source_basename_alias_correct=True,source_checksums_verified=len(checks),official_recipe_sha256_verified=True,patches_applied_without_fuzz=len(queue),core_and_spa_sources_match_deployed_build=True,apkbuild_shell_syntax_passed=True,full_abuild_build_executed=False)
(R/'recipe-prepare-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
