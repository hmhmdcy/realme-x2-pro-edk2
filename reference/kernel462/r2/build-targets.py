"""Build only r2 IMX471 and mux-core objects in new sparse source/O, j2."""
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
spec=importlib.util.spec_from_file_location('build462r2_storage449',HERE.parents[1]/'kernel449/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
SHARED=storage.mount.mounted_build();ORIGINAL=SHARED.parent/'source354'
ISOLATED=SHARED.parent/'kernel462-shared-camera-r2-private';SOURCE=ISOLATED/'source-view';BUILD=ISOLATED/'O'
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel462/r2')
sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
load=lambda path:json.loads(Path(path).read_text())
assert shutil.disk_usage(SHARED).free>=2*1024**3
frozen=load(HERE.parent/'r1-final-validation.json')
for name,digest in frozen['files'].items():assert sha(HERE.parent/name)==digest,name
assert load(PRIVATE.parent/'r1-frozen-files-private.json')==frozen
record=load(HERE.parents[1]/'kernel363/boot-candidate-build-validation.json')
config=(PRIVATE.parent.parent/'kernel457/config363-private').read_bytes()
assert hashlib.sha256(config).hexdigest()==record['artifacts']['.config']['sha256']
manifest=load(PRIVATE/'candidate-manifest-private.json')
for row in manifest['files']:assert sha(PRIVATE/'candidate'/row['path'])==row['candidate_sha256']
tracked=[ORIGINAL/row['path'] for row in manifest['files']]
tracked += [SHARED/name for name in ['.config','Module.symvers','include/generated/autoconf.h','include/config/auto.conf']]
tracked += [SHARED.parent/'kernel462-shared-camera-private/O'/name for name in ['.config','drivers/media/i2c/imx471.o','arch/arm64/boot/dts/qcom/sm8150-samurai.dtb']]
before={str(path):sha(path) for path in tracked}
original_hashes={row['path']:row['sha256'] for row in manifest['inspected_sources']}
assert all(sha(ORIGINAL/name)==digest for name,digest in original_hashes.items())
assert sha(ORIGINAL/'drivers/media/i2c/imx471.c')==next(row['original_sha256'] for row in frozen['candidate'] if row['path'].endswith('imx471.c'))

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
branch(ORIGINAL,SOURCE,{'drivers':{'media':{'i2c':{}},'mux':{}},'include':{'linux':{'mux':{}}}})
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
phases=[];attempt=1
while (PRIVATE/f'target-build-r{attempt}-private.log').exists():attempt+=1
logpath=PRIVATE/f'target-build-r{attempt}-private.log'
ret=0
with logpath.open('xb') as log:
    for target in ['olddefconfig','modules_prepare','drivers/media/i2c/imx471.o','drivers/mux/core.o']:
        assert shutil.disk_usage(SHARED).free>=2*1024**3
        started=time.monotonic();proc=subprocess.Popen(common+[target],env=env,stdout=log,stderr=subprocess.STDOUT)
        print(json.dumps(dict(target=target,pid=proc.pid,started=True,attempt=attempt)),flush=True)
        ret=proc.wait();phases.append(dict(target=target,exit=ret,seconds=round(time.monotonic()-started,3)))
        if ret:break
assert before=={str(path):sha(path) for path in tracked}
assert all(sha(HERE.parent/name)==digest for name,digest in frozen['files'].items())
assert shutil.disk_usage(SHARED).free>=2*1024**3
text=logpath.read_text(errors='replace')
diagnostics=[line for line in text.splitlines() if re.search(r'warning(?:\s|\(|:)|error:',line,re.I)]
report=dict(stage=462,revision='r2',attempt=attempt,phases=phases,exit=ret,kernel_release=record['release'],
    input_config_sha256=hashlib.sha256(config).hexdigest(),private_sparse_source_and_generated_output=True,
    full_source_or_output_copy=False,vmlinux_object_copied_or_linked=False,
    source354_and_shared_generated_inputs_and_frozen_r1_unchanged=True,
    free_bytes_after=shutil.disk_usage(SHARED).free,jobs=2,sdk_or_phone_accessed=False,
    image_or_rootfs_or_full_modules_or_ko_built=False,installed_or_loaded=False,
    candidate=manifest['files'],diagnostics=diagnostics,passed=ret==0 and not diagnostics,
    mux_core_builtin_new_image_required=True,deployable=False)
if not ret:
    report['artifacts']={}
    for name in ['drivers/media/i2c/imx471.o','drivers/mux/core.o']:
        path=BUILD/name;dest=PRIVATE/(path.parent.name+'-'+path.name+'-r'+str(attempt));shutil.copyfile(path,dest)
        report['artifacts'][name]=dict(bytes=path.stat().st_size,sha256=sha(path))
    nm=subprocess.check_output(['aarch64-linux-gnu-nm',str(BUILD/'drivers/mux/core.o')],text=True)
    exports={name:any(line.split()[-1]=='__export_symbol_'+name for line in nm.splitlines() if line.split()) for name in ['mux_state_get','mux_state_put']}
    # Kernel export format can use __ksymtab instead; verify a real generated
    # export record, never infer it from a global T function alone.
    for name in exports:
        exports[name]=exports[name] or any(line.split()[-1]=='__ksymtab_'+name for line in nm.splitlines() if line.split())
    report['new_export_records_in_mux_object']=exports
    available={line.split()[1] for line in (SHARED/'Module.symvers').read_text().splitlines()}
    imported={line.split()[-1] for line in subprocess.check_output(['aarch64-linux-gnu-nm','-u',str(BUILD/'drivers/media/i2c/imx471.o')],text=True).splitlines() if line.split()}
    report['new_imports_absent_old363']=sorted(imported-available-{'__this_module'})
    report['passed']=report['passed'] and all(exports.values()) and report['new_imports_absent_old363']==['mux_state_get','mux_state_put']
(HERE/f'target-build-r{attempt}-validation.json').write_text(json.dumps(report,indent=2)+'\n')
(HERE/'target-build-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
raise SystemExit(0 if report['passed'] else 1)
