"""Compile only the common IOMMU object; keep the installed kernel untouched."""
from pathlib import Path
import hashlib, importlib.util, json, os, shutil, subprocess, time

HERE=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel357')
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
build=storage.mounted_build();source=build.parent/'source354'
attempt=1
while (P/f'object-build-r{attempt}.log').exists():attempt+=1
backup=P/f'object-build-r{attempt}-before';backup.mkdir()
names=['.config','.config.old','Makefile','source','Module.symvers','modules.order',
    'include/generated/compile.h','include/generated/utsversion.h','include/generated/utsrelease.h',
    'include/generated/autoconf.h','include/config/auto.conf','include/config/auto.conf.cmd','include/config/kernel.release',
    'drivers/iommu/of_iommu.o','drivers/iommu/.of_iommu.o.cmd','drivers/iommu/.of_iommu.o.d']
saved={}
for name in names:
    path=build/name
    value=('symlink',os.readlink(path)) if path.is_symlink() else ('file',path.read_bytes()) if path.is_file() else ('missing',None)
    saved[name]=value
    if value[0]=='file':
        copy=backup/name;copy.parent.mkdir(parents=True,exist_ok=True);copy.write_bytes(value[1])
release=(build/'include/config/kernel.release').read_text().strip()
command=['make','-C',str(source),'O='+str(build),'ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-',
    '-j3','W=1','KCFLAGS=-Werror','KERNELRELEASE='+release,'drivers/iommu/of_iommu.o']
env=dict(os.environ,TMPDIR=str(build.parent/'tmp'),KBUILD_BUILD_USER='builder',KBUILD_BUILD_HOST='samurai',
    KBUILD_BUILD_VERSION='298',PATH='/home/cy122/.cargo/bin:'+os.environ['PATH'],RUSTUP_HOME='/home/cy122/.rustup')
log=P/f'object-build-r{attempt}.log';state=P/'object-build-state.json';start=time.monotonic();code=None;artifact=None
try:
    with log.open('xb') as stream:
        child=subprocess.Popen(command,env=env,stdout=stream,stderr=subprocess.STDOUT)
        state.write_text(json.dumps(dict(pid=child.pid,terminal=False,attempt=attempt))+'\n');code=child.wait()
    if not code:
        artifact=P/f'of_iommu-r{attempt}-private.o';shutil.copyfile(build/'drivers/iommu/of_iommu.o',artifact)
finally:
    for name,(kind,data) in saved.items():
        path=build/name
        if path.is_symlink():path.unlink()
        if kind=='file':path.write_bytes(data)
        elif kind=='symlink':
            if path.exists():path.unlink()
            path.symlink_to(data)
        elif path.exists():path.unlink()
report=dict(stage=357,attempt=attempt,exit_code=code,seconds=round(time.monotonic()-start,2),
    diagnostics=[line for line in log.read_text(errors='replace').splitlines() if 'warning:' in line.lower() or 'error:' in line.lower()],
    actual_arm64_kernel_object=True,image_and_module_targets_not_requested=True,
    selected_build_outputs_restored=True,host_preparation_outputs_may_refresh=True,
    installed=False,passed=code==0)
if artifact:report.update(object_bytes=artifact.stat().st_size,object_sha256=hashlib.sha256(artifact.read_bytes()).hexdigest())
state.write_text(json.dumps(dict(pid=child.pid,terminal=True,**report),indent=2)+'\n')
(HERE/'kernel-build-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2));raise SystemExit(code)
