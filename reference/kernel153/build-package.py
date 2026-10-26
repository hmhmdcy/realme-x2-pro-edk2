from pathlib import Path
import hashlib,json,os,re,resource,shutil,subprocess,tarfile
k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
out=Path('/mnt/e/edk2-samurai-out/kernel153')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel153')
report=json.loads((ref/'source-validation.json').read_text())
assert hashlib.sha256((k/report['modified_files'][0]).read_bytes()).hexdigest()==report['candidate_sha256']
assert all(x['exit']==0 for x in json.loads((ref/'actual-function-test-validation.json').read_text())['results'] if x['label']=='candidate153')
assert shutil.disk_usage('/mnt/c').free>8*1024**3
env=os.environ.copy()
env.update(PATH='/home/cy122/.cargo/bin:'+env['PATH'],RUSTUP_HOME='/home/cy122/.rustup',KBUILD_BUILD_VERSION='153')
base=['make','ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','LD=aarch64-linux-gnu-ld --no-keep-memory']
def limit():resource.setrlimit(resource.RLIMIT_AS,(3*1024**3,3*1024**3))
def make(label,args):
    log=out/(label+'-build-private.log')
    assert not log.exists(),log
    with log.open('wb') as f:
        subprocess.run(base+args,cwd=k,env=env,stdout=f,stderr=subprocess.STDOUT,preexec_fn=limit,check=True)
    assert not re.search(r'\b(?:warning|error):',log.read_text()),log
    print('K153_'+label.upper()+'_PASS',flush=True)
patch=ref/'panel-gpio-handoff.patch'
assert patch.read_text().startswith('Subject: [PATCH] drm/panel: sofef03f:')
check=subprocess.run(['scripts/checkpatch.pl','--no-tree','--strict','--no-signoff',str(patch)],cwd=k,capture_output=True,text=True)
(out/'checkpatch.txt').write_text(check.stdout+check.stderr)
assert check.returncode==0,check.stdout+check.stderr
make('panel-w1',['W=1','-j4','drivers/gpu/drm/panel/panel-samsung-sofef03f.o'])
make('full',['-j4','Image','modules','qcom/sm8150-samurai.dtb'])
assert (k/'.config').read_bytes()==(out/'config-before-private').read_bytes()
image=out/'Image-k153-panel-handoff-private'
shutil.copyfile(k/'arch/arm64/boot/Image',image)
assert '#153 SMP PREEMPT' in subprocess.check_output(['strings',str(image)],text=True)
modules=k.parent/'modules-root153'
assert not modules.exists()
modules.mkdir(mode=0o700)
make('install',['INSTALL_MOD_PATH='+str(modules),'INSTALL_MOD_STRIP=1','modules_install'])
release=(k/'include/config/kernel.release').read_text().strip()
(modules/'lib/modules'/release/'build').unlink()
r=subprocess.run(['depmod','-e','-F',str(k/'System.map'),'-b',str(modules),release],capture_output=True)
assert r.returncode==0 and not r.stdout and not r.stderr
with tarfile.open(out.parent/'kernel132/modules-k132-private.tar.gz') as a:
    expected={m.name:a.extractfile(m).read() for m in a if m.isfile() and m.name.endswith('.ko')}
actual={str(p.relative_to(modules)):p.read_bytes() for p in modules.rglob('*.ko')}
assert len(actual)==770 and actual==expected
dtb=k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb'
target=out/'logdump-k153-panel-handoff.img'
assert not target.exists()
shutil.copyfile(out.parent/'kernel147/logdump-k147-iova-align.img',target)
subprocess.run(['mcopy','-o','-i',str(target),str(image),'::/Image'],check=True)
assert subprocess.check_output(['mcopy','-i',str(target),'::/Image','-'])==image.read_bytes()
assert subprocess.check_output(['mcopy','-i',str(target),'::/samurai.dtb','-'])==dtb.read_bytes()
r=subprocess.run(['fsck.fat','-n',str(target)],capture_output=True)
(out/'fat-check.txt').write_bytes(r.stdout+r.stderr)
assert r.returncode==0 and target.stat().st_size==67108864
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
other=subprocess.check_output(['git','diff','--binary','--','.',':(exclude)'+report['modified_files'][0]],cwd=k)
assert other==(out/'other-diff-before-private.patch').read_bytes()
report=dict(stage=153,kernel_build=153,baseline_kernel=147,software_generation=132,
    image_sha256=sha(image),image_bytes=image.stat().st_size,
    logdump_sha256=sha(target),logdump_bytes=target.stat().st_size,
    source_sha256=sha(k/'drivers/gpu/drm/panel/panel-samsung-sofef03f.c'),
    dtb_sha256=sha(dtb),modules770_byte_identical132=True,config_unchanged=True,
    other_tracked_diffs_unchanged=True,build_warnings=0,checkpatch_pass=True,
    fat_check_pass=True,deployed=False,hardware_bug_fixed=False)
(ref/'build-package-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
