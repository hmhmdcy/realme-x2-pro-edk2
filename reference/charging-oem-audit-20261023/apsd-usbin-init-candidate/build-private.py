"""Build a single in-tree temporary diagnostic ko in a private source/O view."""
from pathlib import Path
import hashlib,importlib.util,json,os,re,shutil,subprocess,sys,time
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sys.dont_write_bytecode=True
spec=importlib.util.spec_from_file_location('storage461_init',REF/'kernel461/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
shared=storage.mount.mounted_build();original=(shared/'source').resolve()
private=Path('/home/cy122/charging-management-20261023/apsd-usbin-init-candidate')
source=private/'source-view';build=private/'kbuild';source.mkdir(parents=True,exist_ok=True)
before=sha(shared/'.config');make_before=sha(original/'drivers/power/supply/Makefile')
def branch(src,dst,selected):
 dst.mkdir(exist_ok=True)
 for p in src.iterdir():
  if p.name=='.git':continue
  q=dst/p.name
  if p.name in selected:branch(p,q,selected[p.name])
  elif not q.exists() and not q.is_symlink():q.symlink_to(p,target_is_directory=p.is_dir())
branch(original,source,{'drivers':{'power':{'supply':{}}}})
folder=source/'drivers/power/supply';p=folder/'Makefile'
if p.is_symlink():p.unlink()
p.write_text((original/'drivers/power/supply/Makefile').read_text()+'\n# Private off-only one-bit diagnostic\nobj-m += samurai-usbin-init.o\n')
for n in ['samurai-usbin-init.c','usbin-init-core.h']:
 p=folder/n
 assert not p.is_symlink()
 shutil.copy2(HERE/n,p)
build.mkdir(exist_ok=True)
if not (build/'.config').exists():shutil.copy2(shared/'.config',build/'.config')
for n in ['Module.symvers','vmlinux.symvers']:
 if (shared/n).exists():shutil.copy2(shared/n,build/n)
if not (build/'vmlinux.o').exists():(build/'vmlinux.o').symlink_to(shared/'vmlinux.o')
env=dict(os.environ)
for n in ['KBUILD_EXTMOD','KBUILD_OUTPUT','KCONFIG_CONFIG']:env.pop(n,None)
cmd=['make','-C',str(source),'O='+str(build),'ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','LOCALVERSION=+','W=1','-j4']
phases=[]
with (private/'build.log').open('w') as log:
 for target in ['modules_prepare','drivers/power/supply/samurai-usbin-init.ko']:
  start=time.monotonic();p=subprocess.run([*cmd,target],env=env,stdout=log,stderr=subprocess.STDOUT)
  phases.append(dict(target=target,returncode=p.returncode,seconds=time.monotonic()-start))
  if p.returncode:break
text=(private/'build.log').read_text();diags=[l for l in text.splitlines() if re.search(r'warning:|error:',l,re.I)]
module=build/'drivers/power/supply/samurai-usbin-init.ko'
info=subprocess.check_output(['modinfo',str(module)],text=True) if module.exists() else ''
r=dict(passed=len(phases)==2 and all(p['returncode']==0 for p in phases) and not diags and 'intree:         Y' in info,
 phases=phases,diagnostic_lines=diags,module=str(module),module_sha256=sha(module) if module.exists() else None,modinfo=info,
 files={n:sha(HERE/n) for n in ['samurai-usbin-init.c','usbin-init-core.h']},
 shared_config_unchanged=sha(shared/'.config')==before,shared_makefile_unchanged=sha(original/'drivers/power/supply/Makefile')==make_before,
 phone_accessed=False,ssh_executed=False,sdk_invoked=False,image_or_package_built=False)
(HERE/'build-result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
if not r['passed']:print(text[-6000:]);raise SystemExit(1)
