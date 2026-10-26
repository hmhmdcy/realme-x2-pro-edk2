"""Compile only the PHY object in a private view/output, no SDK/Image."""
from pathlib import Path
import hashlib,importlib.util,json,os,re,shutil,subprocess,sys,time
HERE=Path(__file__).resolve().parent
REF=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sys.dont_write_bytecode=True
spec=importlib.util.spec_from_file_location('storage461_phy',REF/'kernel461/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
shared=storage.mount.mounted_build();original=(shared/'source').resolve()
name='phy-qcom-snps-femto-v2.c';header='phy-qcom-snps-femto-v2-window.h'
assert sha(original/'drivers/phy/qualcomm'/name)=='019dd4759be4955dfae6d92192c2fceb085a4e6945607e4942fb746cf2ab65a9'
before=sha(shared/'.config')
private=Path('/home/cy122/charging-management-20261023/apsd-phy-window-candidate')
source=private/'source-view';build=private/'kbuild';source.mkdir(parents=True,exist_ok=True)
def branch(src,dst,selected):
 dst.mkdir(exist_ok=True)
 for p in src.iterdir():
  if p.name=='.git':continue
  q=dst/p.name
  if p.name in selected:branch(p,q,selected[p.name])
  elif not q.exists() and not q.is_symlink():q.symlink_to(p,target_is_directory=p.is_dir())
branch(original,source,{'drivers':{'phy':{'qualcomm':{}}}})
for n in [name,header]:
 p=source/'drivers/phy/qualcomm'/n
 if p.is_symlink():p.unlink()
 shutil.copy2(HERE/n,p)
build.mkdir(exist_ok=True)
if not (build/'.config').exists():shutil.copy2(shared/'.config',build/'.config')
env=dict(os.environ)
for k in ['KBUILD_EXTMOD','KBUILD_OUTPUT','KCONFIG_CONFIG']:env.pop(k,None)
cmd=['make','-C',str(source),'O='+str(build),'ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','LOCALVERSION=+','W=1','-j4']
phases=[]
with (private/'build.log').open('w') as log:
 for target in ['modules_prepare','drivers/phy/qualcomm/phy-qcom-snps-femto-v2.o']:
  start=time.monotonic();p=subprocess.run([*cmd,target],env=env,stdout=log,stderr=subprocess.STDOUT)
  phases.append(dict(target=target,returncode=p.returncode,seconds=time.monotonic()-start))
  if p.returncode:break
text=(private/'build.log').read_text()
diagnostics=[l for l in text.splitlines() if re.search(r'warning:|error:',l,re.I)]
r=dict(passed=len(phases)==2 and all(p['returncode']==0 for p in phases) and not diagnostics,
 phases=phases,diagnostic_lines=diagnostics,private_source=str(source),private_build=str(build),
 files={n:sha(HERE/n) for n in [name,header,'phy-window.patch']},
 shared_source_unchanged=sha(original/'drivers/phy/qualcomm'/name)=='019dd4759be4955dfae6d92192c2fceb085a4e6945607e4942fb746cf2ab65a9',
 shared_config_unchanged=sha(shared/'.config')==before,
 phone_accessed=False,ssh_executed=False,sdk_invoked=False,image_or_package_built=False)
(HERE/'build-result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
if not r['passed']:print(text[-6000:]);raise SystemExit(1)
