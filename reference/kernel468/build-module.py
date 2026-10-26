"""Build only the private S5K3M5 mode2 module with the original Image363 ABI."""
from pathlib import Path
import hashlib,importlib.util,json,os,re,shutil,subprocess,sys,time
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel468')
spec=importlib.util.spec_from_file_location('build468_storage',HERE.parent/'kernel461/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
SHARED=storage.mount.mounted_build();ORIGINAL=SHARED.parent/'source354'
ISOLATED=SHARED.parent/'kernel468-tele-mode2-private';SOURCE=ISOLATED/'source-view';BUILD=ISOLATED/'O'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_bytes())
assert shutil.disk_usage(SHARED).free>=2*1024**3
record=load(HERE.parent/'kernel363/boot-candidate-build-validation.json');release=record['release']
config=(PRIVATE.parent/'kernel457/config363-private').read_bytes()
assert hashlib.sha256(config).hexdigest()==record['artifacts']['.config']['sha256']
assert sha(SHARED/'Module.symvers')==record['artifacts']['Module.symvers']['sha256']
manifest=load(PRIVATE/'candidate-manifest-private.json');candidate=PRIVATE/'candidate/drivers/media/i2c'
assert sha(candidate/'s5k3m5.c')==manifest['candidate_sha256']
assert sha(candidate/'s5k3m5-19mhz-tables.h')==manifest['header_sha256']
git=lambda *args:subprocess.check_output(['git','-C',str(ORIGINAL),*args],env=dict(os.environ,GIT_OPTIONAL_LOCKS='0'))
headers=['include/media/v4l2-subdev.h','include/media/v4l2-ctrls.h','include/media/v4l2-cci.h',
         'include/linux/pm_runtime.h','include/linux/regulator/consumer.h','include/linux/i2c.h']
assert all(git('show',record['commit']+':'+p)==(ORIGINAL/p).read_bytes() for p in headers)
tracked=[SHARED/p for p in ['.config','Module.symvers','include/config/auto.conf','include/generated/autoconf.h']]
tracked += [ORIGINAL/p for p in ['drivers/media/i2c/s5k3m5.c','drivers/media/i2c/s5k3m5-19mhz-tables.h','drivers/media/i2c/Makefile','drivers/media/i2c/Kconfig']]
before={str(p):sha(p) for p in tracked};head=git('rev-parse','HEAD')
def branch(src,dst,owned):
    dst.mkdir(parents=True,exist_ok=True)
    for path in src.iterdir():
        if path.name=='.git':continue
        target=dst/path.name
        if path.name in owned:
            assert not target.is_symlink();branch(path,target,owned[path.name])
        elif not target.exists() and not target.is_symlink():target.symlink_to(path,target_is_directory=path.is_dir())
ISOLATED.mkdir(exist_ok=True);branch(ORIGINAL,SOURCE,{'drivers':{'media':{'i2c':{}}}})
for name in ['s5k3m5.c','s5k3m5-19mhz-tables.h']:
    target=SOURCE/'drivers/media/i2c'/name
    if target.is_symlink():target.unlink()
    shutil.copyfile(candidate/name,target)
BUILD.mkdir(exist_ok=True)
if not (BUILD/'.config').exists():(BUILD/'.config').write_bytes(config)
for name in ['Module.symvers','vmlinux.symvers']:
    if (SHARED/name).exists() and not (BUILD/name).exists():shutil.copyfile(SHARED/name,BUILD/name)
# Normal in-tree modpost reads this retained object; never link it to shared O.
assert shutil.disk_usage(SHARED).free-(SHARED/'vmlinux.o').stat().st_size>=2*1024**3
if not (BUILD/'vmlinux.o').exists():shutil.copyfile(SHARED/'vmlinux.o',BUILD/'vmlinux.o')
assert not (BUILD/'vmlinux.o').is_symlink() and sha(BUILD/'vmlinux.o')==sha(SHARED/'vmlinux.o')
tmp=ISOLATED/'tmp';tmp.mkdir(exist_ok=True)
env=dict(os.environ,PATH='/home/cy122/.cargo/bin:'+os.environ['PATH'],RUSTUP_HOME='/home/cy122/.rustup',
         KBUILD_BUILD_USER='builder',KBUILD_BUILD_HOST='samurai',KBUILD_BUILD_VERSION='363',TMPDIR=str(tmp))
for key in ['KBUILD_EXTMOD','KBUILD_OUTPUT','KCONFIG_CONFIG']:env.pop(key,None)
common=['make','-C',str(SOURCE),'O='+str(BUILD),'ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-',
        'LOCALVERSION=+','KERNELRELEASE='+release,'W=1','KCFLAGS=-Werror','-j2']
attempt=1
while (PRIVATE/f'module-build-r{attempt}-private.log').exists():attempt+=1
logfile=PRIVATE/f'module-build-r{attempt}-private.log';phases=[];ret=0;begin=time.monotonic()
with logfile.open('xb') as log:
    for target in ['olddefconfig','modules_prepare','drivers/media/i2c/s5k3m5.ko']:
        assert shutil.disk_usage(SHARED).free>=2*1024**3
        targets=[target]
        if target.endswith('/s5k3m5.ko'):
            # CCI is modular in Image363, so normal in-tree modpost needs its
            # unchanged export provider among the selected module targets.
            targets.append('drivers/media/v4l2-core/v4l2-cci.ko')
        start=time.monotonic();proc=subprocess.Popen(common+targets,env=env,stdout=log,stderr=subprocess.STDOUT)
        print(json.dumps(dict(attempt=attempt,target=target,pid=proc.pid,started=True)),flush=True)
        ret=proc.wait();phases.append(dict(target=target,exit=ret,seconds=round(time.monotonic()-start,3)))
        if ret:break
assert head==git('rev-parse','HEAD') and before=={str(p):sha(p) for p in tracked}
configmap=lambda raw:{line.split('=',1)[0]:line for line in raw.decode().splitlines() if line.startswith(('CONFIG_','# CONFIG_'))}
a=configmap(config);b=configmap((BUILD/'.config').read_bytes())
diff={k:[a.get(k),b.get(k)] for k in a.keys()|b.keys() if a.get(k)!=b.get(k)}
assert all('VIDEO_QCOM_CAMSS_ICP' in key for key in diff),diff
diagnostics=[line for line in logfile.read_text(errors='replace').splitlines() if re.search(r'warning(?:\s|\(|:)|error:',line,re.I)]
report=dict(stage=468,attempt=attempt,exit=ret,phases=phases,seconds=round(time.monotonic()-begin,3),
    candidate_sha256=manifest['candidate_sha256'],private_header_sha256=manifest['header_sha256'],
    exact_image363_input_config_sha256=hashlib.sha256(config).hexdigest(),configuration_differences_from_image363=diff,
    kernel_release=release,api_headers_equal_image363=headers,shared_inputs_and_source_unchanged=True,
    sparse_source_and_private_generated_output=True,private_modpost_vmlinux_object_bytes=(BUILD/'vmlinux.o').stat().st_size,
    no_shared_vmlinux_link=True,jobs=2,diagnostics=diagnostics,free_bytes=shutil.disk_usage(SHARED).free,
    image_or_rootfs_or_full_modules_built=False,installed_or_loaded=False,sdk_or_phone_accessed=False,passed=not ret and not diagnostics)
if not ret:
    ko=BUILD/'drivers/media/i2c/s5k3m5.ko';out=PRIVATE/f's5k3m5-mode2-build{attempt}.ko';shutil.copyfile(ko,out)
    info=lambda field:subprocess.check_output(['modinfo','-F',field,str(out)],text=True).strip()
    imported={line.split()[-1] for line in subprocess.check_output(['aarch64-linux-gnu-nm','-u',str(out)],text=True).splitlines() if line.strip()}
    available={line.split()[1] for line in (SHARED/'Module.symvers').read_text().splitlines()}
    assert imported<=available,sorted(imported-available)
    assert info('intree')=='Y' and info('vermagic').split()[0]==release
    sections=subprocess.check_output(['aarch64-linux-gnu-readelf','-S',str(out)],text=True)
    report.update(module_bytes=out.stat().st_size,module_sha256=sha(out),intree=info('intree'),
        vermagic=info('vermagic'),depends=info('depends'),imported_symbols=len(imported),
        all_imports_in_original363_symvers=True,module_versions_section_present='__versions' in sections)
    original_symbols={line.split()[1]:line.split() for line in (SHARED/'Module.symvers').read_text().splitlines()}
    cci_exports=[line.split() for line in (BUILD/'Module.symvers').read_text().splitlines() if line.split()[2].endswith('/v4l2-cci')]
    assert len(cci_exports)==5 and all(row==original_symbols[row[1]] for row in cci_exports)
    report.update(unchanged_modular_cci_provider_built_for_modpost=True,all_five_cci_exports_equal_original363=True,
                  cci_provider_scheduled_for_install=False)
    (PRIVATE/'module-imports-private.json').write_text(json.dumps(sorted(imported),indent=2)+'\n')
(HERE/f'module-build-r{attempt}-validation.json').write_text(json.dumps(report,indent=2)+'\n')
(HERE/'module-build-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2),flush=True);raise SystemExit(0 if report['passed'] else 1)
