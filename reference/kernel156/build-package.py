from pathlib import Path
import hashlib,json,os,re,resource,shlex,shutil,subprocess,tarfile
k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
out=Path('/mnt/e/edk2-samurai-out/kernel156')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel156')
report=json.loads((ref/'source-validation.json').read_text())
for name,sha in report['after_sha256'].items():assert hashlib.sha256((k/name).read_bytes()).hexdigest()==sha,name
tests=json.loads((ref/'actual-function-test-validation.json').read_text())
assert all(x['exit']==0 for x in tests['results'] if x['label']=='candidate156')
assert shutil.disk_usage('/mnt/c').free>8*1024**3
env=os.environ.copy()
env.update(PATH='/home/cy122/.cargo/bin:'+env['PATH'],RUSTUP_HOME='/home/cy122/.rustup',KBUILD_BUILD_VERSION='156')
base=['make','ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','LD=aarch64-linux-gnu-ld --no-keep-memory']
def limit():resource.setrlimit(resource.RLIMIT_AS,(3*1024**3,3*1024**3))
def make(label,args):
    log=out/(label+'-build-private.log');assert not log.exists(),log
    with log.open('wb') as f:subprocess.run(base+args,cwd=k,env=env,stdout=f,stderr=subprocess.STDOUT,preexec_fn=limit,check=True)
    assert not re.search(r'\b(?:warning|error):',log.read_text()),log
    print('K156_'+label.upper()+'_PASS',flush=True)
check=subprocess.run(['scripts/checkpatch.pl','--no-tree','--strict','--no-signoff','--ignore','OPEN_ENDED_LINE',str(ref/'first-frame-backlight.patch')],cwd=k,capture_output=True,text=True)
(out/'checkpatch.txt').write_text(check.stdout+check.stderr)
assert check.returncode==0,check.stdout+check.stderr
make('changed-w1-retry1',['W=1','-j4','drivers/gpu/drm/drm_panel.o','drivers/gpu/drm/bridge/panel.o',
    'drivers/gpu/drm/msm/disp/dpu1/dpu_kms.o','drivers/gpu/drm/panel/panel-samsung-sofef03f.o'])
# Compile assertions using the actual ARM64 kernel types and generated flags.
old=json.loads((out/'source-before-private.json').read_text())['include/drm/drm_panel.h']
start=old.index('struct drm_panel {');end=old.index('\n};',start)+3
old_struct=old[start:end].replace('struct drm_panel {','struct drm_panel_before156 {',1)
layout=out/'panel-layout-private.c'
fields=['dev','backlight','funcs','connector_type','list','followers','follower_lock',
    'prepare_prev_first','prepared','enabled','container','refcount']
layout.write_text('#include <linux/stddef.h>\n#include <drm/drm_panel.h>\n'+old_struct+'\n'+
    '_Static_assert(sizeof(struct drm_panel)==sizeof(struct drm_panel_before156), "panel size");\n'+
    ''.join(f'_Static_assert(offsetof(struct drm_panel,{f})==offsetof(struct drm_panel_before156,{f}), "{f}");\n' for f in fields))
cmdfile=(k/'drivers/gpu/drm/.drm_panel.o.cmd').read_text()
line=next(x for x in cmdfile.splitlines() if x.startswith(('savedcmd_','cmd_')) and ':=' in x)
args=shlex.split(line.split(':=',1)[1].strip().split(';',1)[0])
assert args[0].endswith('gcc') and args[-1]=='drivers/gpu/drm/drm_panel.c',args
args=[x.replace('drivers/gpu/drm/.drm_panel.o.d',str(out/'panel-layout-private.d')) for x in args]
args[args.index('-o')+1]=str(out/'panel-layout-private.o');args[-1]=str(layout)
r=subprocess.run(args,cwd=k,env=env,capture_output=True)
(out/'panel-layout-private.log').write_bytes(r.stdout+r.stderr)
assert r.returncode==0 and not r.stdout and not r.stderr,r.stdout+r.stderr
(ref/'panel-layout-validation.json').write_text(json.dumps(dict(stage=156,actual_arm64_kernel_types=True,
    struct_size_preserved=True,existing_member_offsets_preserved=fields,new_flags_fit_existing_padding=True),indent=2)+'\n')
print('K156_PANEL_LAYOUT_ABI_PASS',flush=True)
make('full',['-j4','Image','modules','qcom/sm8150-samurai.dtb'])
assert (k/'.config').read_bytes()==(out/'config-before-private').read_bytes()
image=out/'Image-k156-first-frame-private';shutil.copyfile(k/'arch/arm64/boot/Image',image)
assert '#156 SMP PREEMPT' in subprocess.check_output(['strings',str(image)],text=True)
modules=k.parent/'modules-root156';assert not modules.exists();modules.mkdir(mode=0o700)
make('install',['INSTALL_MOD_PATH='+str(modules),'INSTALL_MOD_STRIP=1','modules_install'])
release=(k/'include/config/kernel.release').read_text().strip()
(modules/'lib/modules'/release/'build').unlink()
r=subprocess.run(['depmod','-e','-F',str(k/'System.map'),'-b',str(modules),release],capture_output=True)
assert r.returncode==0 and not r.stdout and not r.stderr
with tarfile.open(out.parent/'kernel132/modules-k132-private.tar.gz') as a:
    expected={m.name:a.extractfile(m).read() for m in a if m.isfile() and m.name.endswith('.ko')}
actual={str(p.relative_to(modules)):p.read_bytes() for p in modules.rglob('*.ko')}
assert len(actual)==770 and actual==expected,'Module bytes changed; deploy matching modules before any boot'
dtb=k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb'
target=out/'logdump-k156-first-frame.img';assert not target.exists()
shutil.copyfile(out.parent/'kernel154/logdump-k154-host-init.img',target)
subprocess.run(['mcopy','-o','-i',str(target),str(image),'::/Image'],check=True)
assert subprocess.check_output(['mcopy','-i',str(target),'::/Image','-'])==image.read_bytes()
assert subprocess.check_output(['mcopy','-i',str(target),'::/samurai.dtb','-'])==dtb.read_bytes()
r=subprocess.run(['fsck.fat','-n',str(target)],capture_output=True)
(out/'fat-check.txt').write_bytes(r.stdout+r.stderr)
assert r.returncode==0 and target.stat().st_size==67108864
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(dtb)==json.loads((ref.parent/'kernel154/build-package-validation.json').read_text())['dtb_sha256']
other=subprocess.check_output(['git','diff','--binary','--','.']+[':(exclude)'+n for n in report['modified_files']],cwd=k)
assert other==(out/'other-diff-before-private.patch').read_bytes()
result=dict(stage=156,kernel_build=156,baseline_kernel=154,software_generation=132,
    image_sha256=sha(image),image_bytes=image.stat().st_size,logdump_sha256=sha(target),logdump_bytes=target.stat().st_size,
    source_sha256=report['after_sha256'],dtb_sha256=sha(dtb),dtb_unchanged=True,
    modules770_byte_identical132=True,panel_layout_abi_preserved=True,config_unchanged=True,
    other_tracked_diffs_unchanged=True,build_warnings=0,checkpatch_pass=True,
    checkpatch_ignored_types=['OPEN_ENDED_LINE'],valid_trace_macro_delimiters=True,
    fat_check_pass=True,deployed=False,hardware_bug_fixed=False)
(ref/'build-package-validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result),flush=True)
