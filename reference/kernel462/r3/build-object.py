"""Build only the r3 IMX471 object, with frozen r2 header, isolated j2."""
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

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('build462r3_storage449',HERE.parents[1]/'kernel449/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
SHARED=storage.mount.mounted_build();ORIGINAL=SHARED.parent/'source354'
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel462/r3')
ISOLATED=SHARED.parent/'kernel462-shared-camera-r3-private';SOURCE=ISOLATED/'source-view';BUILD=ISOLATED/'O'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_text())
assert shutil.disk_usage(SHARED).free>=2*1024**3
frozen={}
for part in ['r1','r2']:
    directory=HERE.parent if part=='r1' else HERE.parent/'r2'
    record=load(directory/(part+'-final-validation.json'))
    assert record==load(PRIVATE.parent/('' if part=='r1' else part)/(part+'-frozen-files-private.json'))
    for name,digest in record['files'].items():
        assert sha(directory/name)==digest;frozen[str(directory/name)]=digest
baseline=load(HERE.parents[1]/'kernel363/boot-candidate-build-validation.json')
config=(PRIVATE.parent.parent/'kernel457/config363-private').read_bytes()
assert hashlib.sha256(config).hexdigest()==baseline['artifacts']['.config']['sha256']
manifest=load(PRIVATE/'candidate-manifest-private.json')
candidate=PRIVATE/'candidate/drivers/media/i2c/imx471.c'
assert sha(candidate)==manifest['candidate_sha256']
header=PRIVATE.parent/'r2/candidate/include/linux/mux/consumer.h'
assert sha(header)==next(r['candidate_sha256'] for r in record['candidate'] if r['path'].endswith('consumer.h'))
tracked=[SHARED/n for n in ['.config','Module.symvers','include/generated/autoconf.h','include/config/auto.conf']]
tracked+=[ORIGINAL/n for n in ['drivers/media/i2c/imx471.c','include/linux/mux/consumer.h','drivers/mux/core.c']]
tracked+=[SHARED.parent/'kernel462-shared-camera-r2-private/O'/n for n in ['.config','drivers/media/i2c/imx471.o','drivers/mux/core.o']]
before={str(p):sha(p) for p in tracked}
def branch(src,dst,owned):
    dst.mkdir(parents=True,exist_ok=True)
    for p in src.iterdir():
        if p.name=='.git':continue
        q=dst/p.name
        if p.name in owned:
            assert not q.is_symlink();branch(p,q,owned[p.name])
        elif not q.exists() and not q.is_symlink():q.symlink_to(p,target_is_directory=p.is_dir())
ISOLATED.mkdir(exist_ok=True)
branch(ORIGINAL,SOURCE,{'drivers':{'media':{'i2c':{}}},'include':{'linux':{'mux':{}}}})
for original,relative in [(candidate,'drivers/media/i2c/imx471.c'),(header,'include/linux/mux/consumer.h')]:
    target=SOURCE/relative
    if target.is_symlink():target.unlink()
    shutil.copyfile(original,target)
BUILD.mkdir(exist_ok=True)
if not (BUILD/'.config').exists():(BUILD/'.config').write_bytes(config)
tmp=ISOLATED/'tmp';tmp.mkdir(exist_ok=True)
env=dict(os.environ,PATH='/home/cy122/.cargo/bin:'+os.environ['PATH'],RUSTUP_HOME='/home/cy122/.rustup',
         KBUILD_BUILD_USER='builder',KBUILD_BUILD_HOST='samurai',KBUILD_BUILD_VERSION='363',TMPDIR=str(tmp))
for key in ['KBUILD_EXTMOD','KBUILD_OUTPUT','KCONFIG_CONFIG']:env.pop(key,None)
common=['make','-C',str(SOURCE),'O='+str(BUILD),'ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-',
        'LOCALVERSION=+','KERNELRELEASE='+baseline['release'],'W=1','KCFLAGS=-Werror','-j2']
attempt=1
while (PRIVATE/f'object-build-r{attempt}-private.log').exists():attempt+=1
logpath=PRIVATE/f'object-build-r{attempt}-private.log';phases=[];ret=0
with logpath.open('xb') as log:
    for target in ['olddefconfig','modules_prepare','drivers/media/i2c/imx471.o']:
        assert shutil.disk_usage(SHARED).free>=2*1024**3
        start=time.monotonic();proc=subprocess.Popen(common+[target],stdout=log,stderr=subprocess.STDOUT,env=env)
        print(json.dumps(dict(target=target,pid=proc.pid,attempt=attempt,started=True)),flush=True)
        ret=proc.wait();phases.append(dict(target=target,exit=ret,seconds=round(time.monotonic()-start,3)))
        if ret:break
assert before=={str(p):sha(p) for p in tracked}
assert frozen=={p:sha(p) for p in frozen}
diagnostics=[line for line in logpath.read_text(errors='replace').splitlines() if re.search(r'warning(?:\s|\(|:)|error:',line,re.I)]
report=dict(stage=462,revision='r3',attempt=attempt,phases=phases,exit=ret,passed=ret==0 and not diagnostics,
    candidate_sha256=sha(candidate),r2_consumer_header_sha256=sha(header),diagnostics=diagnostics,jobs=2,
    exact_image363_input_config_sha256=hashlib.sha256(config).hexdigest(),
    source354_shared_generated_and_frozen_r1_r2_inputs_unchanged=True,free_bytes_after=shutil.disk_usage(SHARED).free,
    sparse_source_and_private_generated_O=True,no_full_source_or_output_copy=True,vmlinux_object_copied_or_linked=False,
    ko_or_image_or_rootfs_or_full_modules_built=False,requires_core0064_and_r2_mux_exports=True,
    sdk_or_phone_accessed=False,deployable=False)
if not ret:
    obj=BUILD/'drivers/media/i2c/imx471.o';shutil.copyfile(obj,PRIVATE/f'imx471-r3-build{attempt}.o')
    report['object']=dict(bytes=obj.stat().st_size,sha256=sha(obj))
    available={line.split()[1] for line in (SHARED/'Module.symvers').read_text().splitlines()}
    imported={line.split()[-1] for line in subprocess.check_output(['aarch64-linux-gnu-nm','-u',str(obj)],text=True).splitlines() if line.split()}
    report['missing_old363_imports']=sorted(imported-available-{'__this_module'})
    report['passed']=report['passed'] and report['missing_old363_imports']==['mux_state_get','mux_state_put']
assert shutil.disk_usage(SHARED).free>=2*1024**3
(HERE/f'object-build-r{attempt}-validation.json').write_text(json.dumps(report,indent=2)+'\n')
(HERE/'object-build-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
raise SystemExit(0 if report['passed'] else 1)
