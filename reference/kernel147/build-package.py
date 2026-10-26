from pathlib import Path
import hashlib
import json
import os
import re
import resource
import shutil
import subprocess
import tarfile

k = Path('/home/cy122/pmos-samurai-kernel136/kernel')
out = Path('/mnt/e/edk2-samurai-out/kernel147')
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel147')
assert not (out / 'align-full-build-private.log').exists()
assert shutil.disk_usage('/mnt/c').free > 4 * 1024**3
env = os.environ.copy()
env['PATH'] = '/home/cy122/.cargo/bin:' + env['PATH']
env['RUSTUP_HOME'] = '/home/cy122/.rustup'
env['KBUILD_BUILD_VERSION'] = '147'
base = ['make','ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-',
        'LD=aarch64-linux-gnu-ld --no-keep-memory']

def limit():
    resource.setrlimit(resource.RLIMIT_AS, (3*1024**3,3*1024**3))

def make(label, args):
    path=out / ('align-' + label + '-private.log')
    assert not path.exists()
    with path.open('wb') as f:
        subprocess.run(base+args,cwd=k,env=env,stdout=f,stderr=subprocess.STDOUT,
                       preexec_fn=limit,check=True)
    assert not re.search(r'\b(?:warning|error):',path.read_text())
    print('K147_'+label.upper()+'_PASS',flush=True)

make('msm-build',['W=1','-j6','drivers/gpu/drm/msm/'])
make('full-build',['-j6','Image','modules','qcom/sm8150-samurai.dtb'])
assert (k / '.config').read_bytes() == (out / 'config-before-private').read_bytes()
release=(k / 'include/config/kernel.release').read_text().strip()
assert release=='7.3.0-rc6-rmx1931-samurai-k132+'
image=out / 'Image-k147-iova-align-private'
shutil.copyfile(k / 'arch/arm64/boot/Image',image)
assert '#147 SMP PREEMPT' in subprocess.check_output(['strings',str(image)],text=True)
modules=k.parent / 'modules-root147'
assert not modules.exists()
modules.mkdir(mode=0o700)
make('modules-install',['INSTALL_MOD_PATH='+str(modules),'INSTALL_MOD_STRIP=1','modules_install'])
(modules / 'lib/modules' / release / 'build').unlink()
dep=subprocess.run(['depmod','-e','-F',str(k / 'System.map'),'-b',str(modules),release],capture_output=True)
assert dep.returncode==0 and not dep.stdout and not dep.stderr
with tarfile.open(out.parent / 'kernel132/modules-k132-private.tar.gz') as archive:
    expected={m.name:archive.extractfile(m).read() for m in archive if m.isfile() and m.name.endswith('.ko')}
actual={str(x.relative_to(modules)):x for x in modules.rglob('*.ko')}
assert len(actual)==770 and actual.keys()==expected.keys()
assert all(actual[x].read_bytes()==expected[x] for x in actual)
target=out / 'logdump-k147-iova-align.img'
assert not target.exists()
shutil.copyfile(out.parent / 'kernel145/logdump-k145-dsi-observation.img',target)
subprocess.run(['mcopy','-o','-i',str(target),str(image),'::/Image'],check=True)
assert subprocess.check_output(['mcopy','-i',str(target),'::/Image','-'])==image.read_bytes()
assert subprocess.check_output(['mcopy','-i',str(target),'::/samurai.dtb','-'])==(k / 'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb').read_bytes()
check=subprocess.run(['fsck.fat','-n',str(target)],capture_output=True)
(out / 'fat-check-private.txt').write_bytes(check.stdout+check.stderr)
assert check.returncode==0 and target.stat().st_size==67108864
sha=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
report=dict(stage=147,kernel_build=147,baseline=145,software_generation=132,
    release=release,image_sha256=sha(image),image_bytes=image.stat().st_size,
    logdump_sha256=sha(target),logdump_bytes=target.stat().st_size,
    a640_managed_iova_alignment_64k=True,ccu_invalidation_restored=True,other_source_diffs_unchanged=True,
    modules770_byte_identical132=True,config_unchanged=True,dtb_unchanged=True,
    build_warnings=0,fat_check_pass=True,diagnostic_candidate=True,
    deployed=False,device_fix_accepted=False)
for folder in [ref,out]:
    (folder / 'build-package-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('K147_IMAGE_MODULES_DTB_LOGDUMP_READY',flush=True)
