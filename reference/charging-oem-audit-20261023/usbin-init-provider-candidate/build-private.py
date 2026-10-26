"""One private k363 provider build; no Image, SDK, installation or shared edits."""
from pathlib import Path
import hashlib,importlib.util,json,os,re,shutil,subprocess,sys,time
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
tested=json.loads((HERE/'test-result.json').read_text())
assert tested['passed'] and tested['group_count']==10 and tested['actual_functions']==17
for name,digest in tested['files'].items():assert sha(HERE/name)==digest,name
baseline=json.loads((HERE/'baseline.json').read_text())
sys.dont_write_bytecode=True
spec=importlib.util.spec_from_file_location('usbin_provider_storage284',REF/'kernel284/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
shared=storage.mounted_build();original=shared.parent/'source354'
assert original.is_dir()
assert (shared/'include/config/kernel.release').read_text().strip()=='7.3.0-rc6-rmx1931-samurai-k363+'
old_build=Path('/home/cy122/charging-management-20261023/source-float-candidate/kbuild')
assert sha(old_build/'.config')==baseline['config_sha256']
def config_values(p):return dict(s.split('=',1) for s in p.read_text().splitlines() if s.startswith('CONFIG_'))
assert config_values(shared/'.config')==config_values(old_build/'.config')
private=Path('/home/cy122/charging-management-20261023/usbin-init-provider-candidate')
source=private/'source-view';build=private/'kbuild';source.mkdir(parents=True,exist_ok=True)
tracked=[shared/'.config',original/'drivers/power/supply/Makefile',shared/'Module.symvers',shared/'vmlinux.symvers']
before={str(p):sha(p) for p in tracked if p.exists()}
def branch(src,dst,selected):
 dst.mkdir(exist_ok=True)
 for p in src.iterdir():
  if p.name=='.git':continue
  q=dst/p.name
  if p.name in selected:branch(p,q,selected[p.name])
  elif not q.exists() and not q.is_symlink():q.symlink_to(p,target_is_directory=p.is_dir())
branch(original,source,{'drivers':{'power':{'supply':{}}}})
folder=source/'drivers/power/supply';makefile=folder/'Makefile'
if makefile.is_symlink():makefile.unlink()
makefile.write_text((original/'drivers/power/supply/Makefile').read_text()+'\n# Private default-off minimal USBIN initialization\nobj-m += samurai-usb-input.o\n')
for name in ['samurai-usb-input.c','samurai-usb-input-decode.h','usbin-init-core.h']:
 target=folder/name
 assert not target.is_symlink(),target
 shutil.copy2(HERE/name,target)
build.mkdir(exist_ok=True)
if not (build/'.config').exists():shutil.copy2(old_build/'.config',build/'.config')
for name in ['Module.symvers','vmlinux.symvers']:
 if (shared/name).exists():shutil.copy2(shared/name,build/name)
if not (build/'vmlinux.o').exists():(build/'vmlinux.o').symlink_to(shared/'vmlinux.o')
assert (build/'vmlinux.o').resolve()==(shared/'vmlinux.o').resolve()
env=dict(os.environ)
for name in ['KBUILD_EXTMOD','KBUILD_OUTPUT','KCONFIG_CONFIG']:env.pop(name,None)
cmd=['make','-C',str(source),'O='+str(build),'ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','LOCALVERSION=+','W=1','-j4']
phases=[]
with (private/'build.log').open('w') as log:
 for target in ['modules_prepare','drivers/power/supply/samurai-usb-input.ko']:
  started=time.monotonic();p=subprocess.run([*cmd,target],env=env,stdout=log,stderr=subprocess.STDOUT)
  phases.append(dict(target=target,returncode=p.returncode,seconds=time.monotonic()-started))
  if p.returncode:break
log=(private/'build.log').read_text();diagnostics=[s for s in log.splitlines() if re.search(r'warning:|error:|undefined!',s,re.I)]
module=build/'drivers/power/supply/samurai-usb-input.ko'
info=subprocess.check_output(['modinfo',str(module)],text=True) if module.exists() else ''
unchanged=all(sha(Path(p))==h for p,h in before.items())
passed=len(phases)==2 and all(p['returncode']==0 for p in phases) and not diagnostics and unchanged and 'intree:         Y' in info and '7.3.0-rc6-rmx1931-samurai-k363+' in info
passed=passed and sha(build/'.config')==baseline['config_sha256']
r=dict(passed=passed,module=str(module),module_sha256=sha(module) if module.exists() else None,modinfo=info,
 phases=phases,diagnostic_lines=diagnostics,private_build_log=str(private/'build.log'),private_build_log_sha256=sha(private/'build.log'),
 source_root=str(original),shared_inputs_before=before,shared_inputs_unchanged=unchanged,config_sha256=sha(build/'.config'),
 configuration_differences={},shared_config_sha256=sha(shared/'.config'),baseline_config_sha256=baseline['config_sha256'],
 files={name:sha(HERE/name) for name in ['samurai-usb-input.c','samurai-usb-input-decode.h','usbin-init-core.h','build-private.py']},
 test_receipt_sha256=sha(HERE/'test-result.json'),installed=False,image_built=False,sdk_invoked=False,phone_accessed=False)
(HERE/'build-result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
if not passed:print(log[-6000:]);raise SystemExit(1)
