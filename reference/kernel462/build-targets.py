"""Build only isolated IMX471 object, board DTB and changed binding, -j2."""
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
spec=importlib.util.spec_from_file_location('build462_storage449',HERE.parent/'kernel449/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
SHARED=storage.mount.mounted_build();ORIGINAL=SHARED.parent/'source354'
ISOLATED=SHARED.parent/'kernel462-shared-camera-private';SOURCE=ISOLATED/'source-view';BUILD=ISOLATED/'O'
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel462')
sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
load=lambda path:json.loads(Path(path).read_text())
assert shutil.disk_usage(SHARED).free>=2*1024**3
record=load(HERE.parent/'kernel363/boot-candidate-build-validation.json')
config=(PRIVATE.parent/'kernel457/config363-private').read_bytes()
assert hashlib.sha256(config).hexdigest()==record['artifacts']['.config']['sha256']
assert sha(SHARED/'Module.symvers')==record['artifacts']['Module.symvers']['sha256']
manifest=load(PRIVATE/'candidate-manifest-private.json')
tracked=[ORIGINAL/row['path'] for row in manifest['files']]
tracked += [SHARED/name for name in ['.config','Module.symvers','include/generated/autoconf.h','include/config/auto.conf']]
before={str(path):sha(path) for path in tracked}
for row in manifest['files']:
    assert sha(ORIGINAL/row['path'])==row['original_sha256']
    assert sha(PRIVATE/'candidate'/row['path'])==row['candidate_sha256']
api=['include/linux/reset.h','include/linux/mux/consumer.h','include/linux/clk.h','include/linux/regulator/consumer.h']
for name in api:
    assert (ORIGINAL/name).read_bytes()==subprocess.check_output(['git','-C',str(ORIGINAL),'show',record['commit']+':'+name])

def branch(src,dst,owned):
    dst.mkdir(parents=True,exist_ok=True)
    for path in src.iterdir():
        if path.name=='.git':continue
        target=dst/path.name
        if path.name in owned:
            assert not target.is_symlink()
            branch(path,target,owned[path.name])
        elif not target.exists() and not target.is_symlink():
            target.symlink_to(path,target_is_directory=path.is_dir())

ISOLATED.mkdir(exist_ok=True)
branch(ORIGINAL,SOURCE,{'drivers':{'media':{'i2c':{}}},'arch':{'arm64':{'boot':{'dts':{'qcom':{}}}}},
    'Documentation':{'devicetree':{'bindings':{'media':{'i2c':{}}}}}})
for row in manifest['files']:
    target=SOURCE/row['path']
    if target.is_symlink():target.unlink()
    shutil.copyfile(PRIVATE/'candidate'/row['path'],target)
BUILD.mkdir(exist_ok=True)
if not (BUILD/'.config').exists():(BUILD/'.config').write_bytes(config)
tmp=ISOLATED/'tmp';tmp.mkdir(exist_ok=True)
env=dict(os.environ,PATH='/home/cy122/.cargo/bin:'+os.environ['PATH'],RUSTUP_HOME='/home/cy122/.rustup',
         KBUILD_BUILD_USER='builder',KBUILD_BUILD_HOST='samurai',KBUILD_BUILD_VERSION='363',TMPDIR=str(tmp))
for key in ['KBUILD_EXTMOD','KBUILD_OUTPUT','KCONFIG_CONFIG']:env.pop(key,None)
common=['make','-C',str(SOURCE),'O='+str(BUILD),'ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-',
        'LOCALVERSION=+','KERNELRELEASE='+record['release'],'W=1','KCFLAGS=-Werror','-j2']
phases=[]
attempt=1
while (PRIVATE/f'target-build-r{attempt}-private.log').exists():attempt+=1
logpath=PRIVATE/f'target-build-r{attempt}-private.log'
targets=['olddefconfig','modules_prepare','drivers/media/i2c/imx471.o','qcom/sm8150-samurai.dtb']
ret=0
with logpath.open('xb') as log:
    for target in targets:
        assert shutil.disk_usage(SHARED).free>=2*1024**3
        start=time.monotonic();proc=subprocess.Popen(common+[target],env=env,stdout=log,stderr=subprocess.STDOUT)
        print(json.dumps(dict(target=target,pid=proc.pid,started=True,attempt=attempt)),flush=True)
        ret=proc.wait();phases.append(dict(target=target,exit=ret,seconds=round(time.monotonic()-start,3)))
        if ret:break
assert before=={str(path):sha(path) for path in tracked}
assert shutil.disk_usage(SHARED).free>=2*1024**3
text=logpath.read_text(errors='replace')
diagnostics=[line for line in text.splitlines() if re.search(r'warning(?:\s|\(|:)|error:',line,re.I)]
report=dict(stage=462,attempt=attempt,phases=phases,exit=ret,kernel_release=record['release'],
    api_headers_equal_image363=True,headers=api,input_config_sha256=hashlib.sha256(config).hexdigest(),
    private_sparse_source_and_generated_output=True,full_source_or_output_copy=False,vmlinux_object_copied_or_linked=False,
    source354_and_shared_generated_inputs_unchanged=True,free_ge_2gib_after=True,jobs=2,sdk_or_phone_accessed=False,
    image_or_rootfs_or_full_modules_built=False,module_ko_built=False,installed_or_loaded=False,
    candidate=manifest['files'],diagnostics=diagnostics,passed=ret==0)
if not ret:
    artifacts={}
    for name in ['drivers/media/i2c/imx471.o','arch/arm64/boot/dts/qcom/sm8150-samurai.dtb']:
        path=BUILD/name;dest=PRIVATE/(path.name+'-r'+str(attempt));shutil.copyfile(path,dest)
        artifacts[name]=dict(bytes=path.stat().st_size,sha256=sha(path))
    report['artifacts']=artifacts
(HERE/f'target-build-r{attempt}-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
raise SystemExit(ret)
