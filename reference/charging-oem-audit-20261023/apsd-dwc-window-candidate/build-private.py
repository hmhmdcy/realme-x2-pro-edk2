"""Compile only affected DWC objects in a private source view/O directory."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
REF=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sys.dont_write_bytecode=True
spec=importlib.util.spec_from_file_location('storage461_window',REF/'kernel461/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
shared=storage.mount.mounted_build();original=(shared/'source').resolve()
private=Path('/home/cy122/charging-management-20261023/apsd-dwc-window-candidate')
source=private/'source-view';build=private/'kbuild';source.mkdir(parents=True,exist_ok=True)
baseline=json.loads((HERE/'baseline.json').read_bytes())
for row in baseline['files']:
 assert sha(original/'drivers/usb/dwc3'/row['file'])==row['sha256']


def branch(src,dst,names):
 dst.mkdir(exist_ok=True)
 for p in src.iterdir():
  if p.name=='.git':continue
  q=dst/p.name
  if p.name in names:branch(p,q,names[p.name])
  elif not q.exists() and not q.is_symlink():q.symlink_to(p,target_is_directory=p.is_dir())


branch(original,source,{'drivers':{'usb':{'dwc3':{}}}})
for name in ['core.h','core.c','gadget.c']:
 target=source/'drivers/usb/dwc3'/name
 if target.is_symlink():target.unlink()
 shutil.copy2(HERE/name,target)
build.mkdir(exist_ok=True)
if not (build/'.config').exists():shutil.copy2(shared/'.config',build/'.config')
config_before=sha(shared/'.config')
env=dict(os.environ)
for k in ['KBUILD_EXTMOD','KBUILD_OUTPUT','KCONFIG_CONFIG']:env.pop(k,None)
cmd=['make','-C',str(source),'O='+str(build),'ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-',
     'LOCALVERSION=+','W=1','-j4']
phases=[];start=time.monotonic()
with (private/'build.log').open('w') as log:
 for target in ['modules_prepare','drivers/usb/dwc3/core.o','drivers/usb/dwc3/gadget.o',
                'drivers/usb/dwc3/dwc3-qcom-legacy.o','drivers/usb/dwc3/dwc3-qcom.o']:
  t=time.monotonic();q=subprocess.run([*cmd,target],env=env,stdout=log,stderr=subprocess.STDOUT)
  phases.append({'target':target,'exit_code':q.returncode,'seconds':time.monotonic()-t})
  if q.returncode:break
text=(private/'build.log').read_text()
result=dict(passed=all(p['exit_code']==0 for p in phases) and len(phases)==5,
 phases=phases,seconds=time.monotonic()-start,private_source=str(source),private_output=str(build),
 build_log=str(private/'build.log'),sources={n:sha(HERE/n) for n in ['core.h','core.c','gadget.c']},
 shared_source_unchanged=all(sha(original/'drivers/usb/dwc3'/r['file'])==r['sha256'] for r in baseline['files']),
 shared_config_unchanged=sha(shared/'.config')==config_before,sdk_invoked=False,phone_accessed=False,ssh_executed=False,
 image_or_package_built=False,diagnostic_lines=[line for line in text.splitlines() if re.search(r'warning:|error:',line,re.I)])
(HERE/'build-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2));
if not result['passed']:print(text[-7000:])
raise SystemExit(0 if result['passed'] else 1)
