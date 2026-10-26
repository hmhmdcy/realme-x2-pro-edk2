"""Compile only affected built-in bq object in private source/O, no Image."""
from pathlib import Path
import hashlib,importlib.util,json,os,re,shutil,subprocess,sys,time
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
t=json.loads((HERE/'test-result.json').read_text());assert t['passed'] and t['group_count']==6
for n,h in t['files'].items():assert sha(HERE/n)==h,n
sys.dont_write_bytecode=True
spec=importlib.util.spec_from_file_location('current_object_storage284',REF/'kernel284/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
shared=storage.mounted_build();original=shared.parent/'source354'
assert sha(original/'drivers/power/supply/bq27xxx_battery.c')=='b2cd415a995cb196559c0e4981988f737c17c98486449659d168314926aec69e'
tracked=[shared/'.config',shared/'Module.symvers',original/'drivers/power/supply/Makefile',original/'drivers/power/supply/bq27xxx_battery.c',original/'drivers/power/supply/bq27xxx_battery_i2c.c',original/'include/linux/power/bq27xxx_battery.h']
before={str(p):sha(p) for p in tracked if p.exists()}
private=Path('/home/cy122/charging-management-20261023/gauge-current-samurai-candidate');source=private/'source-view';build=private/'kbuild';source.mkdir(parents=True,exist_ok=True)
def branch(src,dst,selected):
 dst.mkdir(exist_ok=True)
 for p in src.iterdir():
  if p.name=='.git':continue
  q=dst/p.name
  if p.name in selected:branch(p,q,selected[p.name])
  elif not q.exists() and not q.is_symlink():q.symlink_to(p,target_is_directory=p.is_dir())
branch(original,source,{'drivers':{'power':{'supply':{}}}})
target=source/'drivers/power/supply/bq27xxx_battery.c'
if target.is_symlink():target.unlink()
shutil.copy2(HERE/'bq27xxx_battery.c',target)
build.mkdir(exist_ok=True)
if not (build/'.config').exists():shutil.copy2(shared/'.config',build/'.config')
env=dict(os.environ)
for name in ['KBUILD_EXTMOD','KBUILD_OUTPUT','KCONFIG_CONFIG']:env.pop(name,None)
command=['make','-C',str(source),'O='+str(build),'ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','LOCALVERSION=+','W=1','-j4']
phases=[]
with (private/'build.log').open('w') as log:
 for name in ['modules_prepare','drivers/power/supply/bq27xxx_battery.o']:
  start=time.monotonic();p=subprocess.run([*command,name],env=env,stdout=log,stderr=subprocess.STDOUT)
  phases.append(dict(target=name,returncode=p.returncode,seconds=time.monotonic()-start))
  if p.returncode:break
text=(private/'build.log').read_text();diagnostics=[s for s in text.splitlines() if re.search(r'warning:|error:',s,re.I)]
obj=build/'drivers/power/supply/bq27xxx_battery.o'
def cfg(p):return dict(s.split('=',1) for s in p.read_text().splitlines() if s.startswith('CONFIG_'))
unchanged=all(sha(Path(p))==h for p,h in before.items())
passed=len(phases)==2 and all(p['returncode']==0 for p in phases) and not diagnostics and unchanged and obj.exists() and cfg(build/'.config')==cfg(shared/'.config')
r=dict(passed=passed,phases=phases,diagnostic_lines=diagnostics,object_private=str(obj),object_sha256=sha(obj) if obj.exists() else None,
 source_sha256=sha(HERE/'bq27xxx_battery.c'),test_receipt_sha256=sha(HERE/'test-result.json'),private_source=str(source),private_build=str(build),
 build_log_private=str(private/'build.log'),build_log_sha256=sha(private/'build.log'),shared_inputs_before=before,shared_inputs_unchanged=unchanged,
 private_config_sha256=sha(build/'.config'),configuration_differences={},Image_or_ko_linked=False,installed=False,SDK_invoked=False,Git_invoked=False,phone_accessed=False)
(HERE/'build-result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
if not passed:print(text[-5000:]);raise SystemExit(1)
