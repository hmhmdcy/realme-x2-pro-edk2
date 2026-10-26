"""Only private gadget.o, using original Image363 core and private new header."""
from pathlib import Path
import hashlib,importlib.util,json,os,re,shutil,subprocess,sys,time
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
t=json.loads((HERE/'test-result.json').read_text());assert t['passed'] and t['group_count']==11
for name,digest in t['files'].items():assert sha(HERE/name)==digest,name
baseline=json.loads((HERE/'source-result.json').read_text())
sys.dont_write_bytecode=True
spec=importlib.util.spec_from_file_location('storage284_sync_recovery',REF/'kernel284/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
shared=storage.mounted_build();original=shared.parent/'source354'
for name,row in baseline['original'].items():assert sha(original/'drivers/usb/dwc3'/name)==row['sha256'],name
tracked=[shared/'.config',shared/'Module.symvers',original/'drivers/usb/dwc3/Makefile',*[original/'drivers/usb/dwc3'/n for n in ['core.c','core.h','gadget.c']]]
before={str(p):sha(p) for p in tracked if p.exists()}
private=Path('/home/cy122/charging-management-20261023/dwc-device-sync-recovery-candidate')
source=private/'source-view';build=private/'kbuild';source.mkdir(parents=True,exist_ok=True)
def branch(src,dst,selected):
 dst.mkdir(exist_ok=True)
 for p in src.iterdir():
  if p.name=='.git':continue
  q=dst/p.name
  if p.name in selected:branch(p,q,selected[p.name])
  elif not q.exists() and not q.is_symlink():q.symlink_to(p,target_is_directory=p.is_dir())
branch(original,source,{'drivers':{'usb':{'dwc3':{}}}})
for name in ['core.h','gadget.c']:
 target=source/'drivers/usb/dwc3'/name
 if target.is_symlink():target.unlink()
 shutil.copy2(HERE/name,target)
assert (source/'drivers/usb/dwc3/core.c').is_symlink()
assert sha(source/'drivers/usb/dwc3/core.c')==baseline['original']['core.c']['sha256']
build.mkdir(exist_ok=True)
if not (build/'.config').exists():shutil.copy2(shared/'.config',build/'.config')
env=dict(os.environ)
for name in ['KBUILD_EXTMOD','KBUILD_OUTPUT','KCONFIG_CONFIG']:env.pop(name,None)
command=['make','-C',str(source),'O='+str(build),'ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','LOCALVERSION=+','W=1','-j4']
phases=[]
with (private/'build.log').open('w') as log:
 for target in ['modules_prepare','drivers/usb/dwc3/gadget.o']:
  started=time.monotonic();p=subprocess.run([*command,target],env=env,stdout=log,stderr=subprocess.STDOUT)
  phases.append(dict(target=target,returncode=p.returncode,seconds=time.monotonic()-started))
  if p.returncode:break
log=(private/'build.log').read_text();diagnostics=[s for s in log.splitlines() if re.search(r'warning:|error:',s,re.I)]
obj=build/'drivers/usb/dwc3/gadget.o'
def configs(p):return dict(s.split('=',1) for s in p.read_text().splitlines() if s.startswith('CONFIG_'))
unchanged=all(sha(Path(p))==h for p,h in before.items())
passed=len(phases)==2 and all(p['returncode']==0 for p in phases) and not diagnostics and unchanged and obj.exists() and configs(shared/'.config')==configs(build/'.config')
r=dict(passed=passed,phases=phases,object_private=str(obj),object_sha256=sha(obj) if obj.exists() else None,
 diagnostic_lines=diagnostics,build_log_private=str(private/'build.log'),build_log_sha256=sha(private/'build.log'),
 private_source=str(source),private_output=str(build),sources={n:sha(HERE/n) for n in ['core.h','gadget.c','build-private.py']},
 original_core_sha256=sha(source/'drivers/usb/dwc3/core.c'),shared_inputs_before=before,shared_inputs_unchanged=unchanged,
 private_config_sha256=sha(build/'.config'),shared_config_sha256=sha(shared/'.config'),configuration_differences={},
 test_receipt_sha256=sha(HERE/'test-result.json'),image_or_ko_linked=False,installed=False,SDK_invoked=False,phone_accessed=False,Git_invoked=False)
(HERE/'build-result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
if not passed:print(log[-6000:]);raise SystemExit(1)
