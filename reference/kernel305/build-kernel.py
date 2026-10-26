"""Build just the sensor module against the verified preserved kernel output."""
from pathlib import Path
import hashlib,importlib.util,json,os,shutil,subprocess,time,stat
import host
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
BUILD=storage.mounted_build()
TREE=Path('/home/cy122/x2pro-linux/camera305-sensor-kernel')
source=TREE/'drivers/media/i2c/s5k3m5.c'
expected=json.loads((HERE/'kernel-source-validation.json').read_text())
assert hashlib.sha256(source.read_bytes()).hexdigest()==expected['source_sha256']
release=(BUILD/'include/config/kernel.release').read_text().strip()
assert release=='7.3.0-rc6-rmx1931-samurai-k298+'
names=['arch/arm64/boot/Image','arch/arm64/boot/dts/qcom/sm8150-samurai.dtb','Module.symvers','.config']
before={n:hashlib.sha256((BUILD/n).read_bytes()).hexdigest() for n in names}
assert before['arch/arm64/boot/Image']=='eb8054e69991528cad4f126d7723b7ef4869b288fb85c992f4803cbfeab5ddaf'
old=BUILD/'drivers/media/i2c/s5k3m5.ko'
backup=host.PRIVATE/'s5k3m5-original-build-private.ko'
if not backup.exists():shutil.copyfile(old,backup)
assert any('\tcci_write\t' in line for line in (BUILD/'Module.symvers').read_text().splitlines())
prefixes={'drivers/media/i2c':('s5k3m5','.s5k3m5'),
          'drivers/media/v4l2-core':('v4l2-cci','.v4l2-cci')}
def outputs():
 return {p for directory,starts in prefixes.items() for p in (BUILD/directory).iterdir()
         if p.is_file() and p.name.startswith(starts)}
saved_names=['.config','.config.old','Module.symvers','modules.order',
 'include/generated/compile.h','include/generated/utsversion.h','include/generated/utsrelease.h',
 'include/generated/autoconf.h','include/config/auto.conf','include/config/auto.conf.cmd',
 'include/config/kernel.release','drivers/media/i2c/modules.order','drivers/media/i2c/Module.symvers',
 'drivers/media/v4l2-core/modules.order','drivers/media/v4l2-core/Module.symvers']
saved={str(p.relative_to(BUILD)):(p.read_bytes(),stat.S_IMODE(p.stat().st_mode))
       for p in outputs()|{BUILD/n for n in saved_names} if p.is_file()}
env=dict(os.environ,PATH='/home/cy122/.cargo/bin:'+os.environ['PATH'],RUSTUP_HOME='/home/cy122/.rustup',
 KBUILD_BUILD_VERSION='298',KBUILD_BUILD_USER='builder',KBUILD_BUILD_HOST='samurai',TMPDIR=str(BUILD.parent/'tmp'))
command=['make','-C',str(TREE),'O='+str(BUILD),'ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','-j3','W=1',
         'KCFLAGS=-Werror','KERNELRELEASE='+release,
         'drivers/media/v4l2-core/v4l2-cci.ko',
         'drivers/media/i2c/s5k3m5.ko']
attempt=1
while (host.PRIVATE/f'sensor-build-r{attempt}-private.log').exists():attempt+=1
log=host.PRIVATE/f'sensor-build-r{attempt}-private.log'
start=time.monotonic()
backup_dir=host.PRIVATE/f'sensor-build-r{attempt}-before-private';backup_dir.mkdir()
for name,(data,mode) in saved.items():
 p=backup_dir/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
try:
 with log.open('xb') as output:
    child=subprocess.Popen(command,env=env,stdout=output,stderr=subprocess.STDOUT)
    (host.PRIVATE/'sensor-build-state-private.json').write_text(json.dumps(dict(pid=child.pid,terminal=False))+'\n')
    code=child.wait()
 if code==0:
    target=host.PRIVATE/'s5k3m5-geometry305-intree-private.ko';shutil.copyfile(old,target)
finally:
 for p in outputs():
    if str(p.relative_to(BUILD)) not in saved:p.unlink()
 for name,(data,mode) in saved.items():
    p=BUILD/name;p.write_bytes(data);p.chmod(mode)
(host.PRIVATE/'sensor-build-state-private.json').write_text(json.dumps(dict(pid=child.pid,terminal=True,exit=code))+'\n')
after={n:hashlib.sha256((BUILD/n).read_bytes()).hexdigest() for n in names}
diagnostics=[s for s in log.read_text(errors='replace').splitlines() if 'warning:' in s.lower() or 'error:' in s.lower()]
report=dict(stage=305,attempt=attempt,exit_code=code,seconds=round(time.monotonic()-start,2),diagnostics=diagnostics,
 source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),kernel_release=release,
 preserved_build_files_before=before,preserved_build_files_after=after,
 image_dtb_symvers_config_unchanged=before==after,not_installed=True,not_full_kernel_build=True)
if code==0:
    info=lambda key:subprocess.check_output(['modinfo','-F',key,str(target)],text=True).strip()
    original_info=lambda key:subprocess.check_output(['modinfo','-F',key,str(host.PRIVATE/'s5k3m5-original-phone-private.ko')],text=True).strip()
    assert info('intree')=='Y' and info('vermagic')==original_info('vermagic')
    available={line.split()[1] for line in saved['Module.symvers'][0].decode().splitlines() if line.strip()}
    imports={line.split()[-1] for line in subprocess.check_output(['aarch64-linux-gnu-nm','-u',str(target)],text=True).splitlines() if line.strip()}
    assert imports<=available,imports-available
    report.update(module_bytes=target.stat().st_size,module_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                  intree=True,vermagic=info('vermagic'),imports_available=True,build_outputs_restored=True)
(HERE/'kernel-build-validation.json').write_text(json.dumps(report,indent=2)+'\n')
(HERE/f'kernel-build-r{attempt}-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
assert code==0 and not diagnostics and before==after
