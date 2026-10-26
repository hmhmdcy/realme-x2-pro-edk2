"""Private k363 in-tree build of only the reviewed USB FLOAT decoder fix."""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

REF = Path(__file__).resolve().parent
CANDIDATE = REF.parent / 'charging-oem-audit-20261023/source-float-candidate'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
tested = json.loads((CANDIDATE/'test-result.json').read_bytes())
assert tested['asan_ubsan'] and tested['patch_dry_run_private_copy']
assert tested['tests'][0]['candidate_assertions'] == 12768 and tested['tests'][0]['actual_float_100000_resolves_sdp']
assert tested['tests'][1]['actual_oem_function_assertions'] == 14
expected = tested['header_sha256']
assert sha(CANDIDATE/'samurai-usb-input-decode.h') == expected
assert sha(REF/'samurai-usb-input.c') == 'b712764fbd4ab24475ae1ba030ee4c26c7eb048a6038488a5435b44ef7eb7098'
sys.path.insert(0, str(REF.parent/'kernel284'))
import storage
shared = storage.mounted_build()
original = shared.parent/'source354'
private = Path('/home/cy122/charging-management-20261023/source-float-candidate')
source, build = private/'source-view', private/'kbuild'
source.mkdir(parents=True,exist_ok=True)

def branch(src,dst,names):
    dst.mkdir(exist_ok=True)
    for p in src.iterdir():
        if p.name=='.git':continue
        q=dst/p.name
        if p.name in names:branch(p,q,names[p.name])
        elif not q.exists() and not q.is_symlink():q.symlink_to(p,target_is_directory=p.is_dir())

branch(original,source,{'drivers':{'power':{'supply':{}}}})
supply=source/'drivers/power/supply';mk=supply/'Makefile'
if mk.is_symlink():mk.unlink()
mk.write_text((original/'drivers/power/supply/Makefile').read_text()+'\nobj-m += samurai-usb-input.o\n')
for origin in [REF/'samurai-usb-input.c', CANDIDATE/'samurai-usb-input-decode.h']:
    target=supply/origin.name
    assert not target.is_symlink()
    shutil.copy2(origin,target)
build.mkdir(exist_ok=True)
if not (build/'.config').exists():shutil.copy2(shared/'.config',build/'.config')
for name in ['Module.symvers','vmlinux.symvers']:
    if (shared/name).exists():shutil.copy2(shared/name,build/name)
if not (build/'vmlinux.o').exists():(build/'vmlinux.o').symlink_to(shared/'vmlinux.o')
assert (build/'vmlinux.o').resolve()==(shared/'vmlinux.o').resolve()
env=dict(os.environ)
for key in ['KBUILD_EXTMOD','KBUILD_OUTPUT','KCONFIG_CONFIG']:env.pop(key,None)
command=['make','-C',str(source),'O='+str(build),'ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','LOCALVERSION=+','W=1','-j4']
with (private/'build.log').open('w') as log:
    for target in ['modules_prepare','drivers/power/supply/samurai-usb-input.ko']:
        result=subprocess.run(command+[target],env=env,stdout=log,stderr=subprocess.STDOUT)
        if result.returncode:
            print((private/'build.log').read_text()[-4000:]);raise SystemExit(result.returncode)
log=(private/'build.log').read_text();assert not re.search(r'warning:|error:|undefined!',log,re.I)
ko=build/'drivers/power/supply/samurai-usb-input.ko'
info=subprocess.check_output(['modinfo',str(ko)],text=True)
release=(shared/'include/config/kernel.release').read_text().strip()
assert release=='7.3.0-rc6-rmx1931-samurai-k363+' and release in info and 'intree:         Y' in info
def configs(p):return {x.split('=',1)[0]:x.split('=',1)[1] for x in p.read_text().splitlines() if x.startswith('CONFIG_')}
assert configs(shared/'.config')==configs(build/'.config')
result={'passed':True,'installed':False,'module':str(ko),'module_sha256':sha(ko),'modinfo':info,
        'sources':{'samurai-usb-input.c':sha(REF/'samurai-usb-input.c'),'samurai-usb-input-decode.h':expected},
        'test_receipt_sha256':sha(CANDIDATE/'test-result.json'),'config_sha256':sha(build/'.config'),
        'configuration_differences':{},'shared_source_modified':False,'phone_accessed':False}
(REF/'source-float-build-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
