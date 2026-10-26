from pathlib import Path
import hashlib,json,os,re,resource,shutil,struct,subprocess,tarfile
k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
out=Path('/mnt/e/edk2-samurai-out/kernel157')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel157')
source=json.loads((ref/'source-validation.json').read_text())
for n,sha in source['after_sha256'].items():assert hashlib.sha256((k/n).read_bytes()).hexdigest()==sha,n
base156=json.loads((ref.parent/'kernel156/build-package-validation.json').read_text())
for n,sha in base156['source_sha256'].items():assert hashlib.sha256((k/n).read_bytes()).hexdigest()==sha,n
tests=json.loads((ref/'actual-function-test-validation.json').read_text())
assert all(r['exit']==0 and r['cases']==15 for r in tests['results'] if r['label']=='candidate157')
assert shutil.disk_usage('/mnt/c').free>8*1024**3
env=os.environ.copy();env.update(PATH='/home/cy122/.cargo/bin:'+env['PATH'],RUSTUP_HOME='/home/cy122/.rustup',KBUILD_BUILD_VERSION='157')
base=['make','ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','LD=aarch64-linux-gnu-ld --no-keep-memory']
def limit():resource.setrlimit(resource.RLIMIT_AS,(3*1024**3,3*1024**3))
def make(label,args):
    log=out/(label+'-build-private.log');assert not log.exists(),log
    with log.open('wb') as f:subprocess.run(base+args,cwd=k,env=env,stdout=f,stderr=subprocess.STDOUT,preexec_fn=limit,check=True)
    assert not re.search(r'\b(?:warning|error):',log.read_text()),log
    print('K157_'+label.upper()+'_PASS',flush=True)
check=subprocess.run(['scripts/checkpatch.pl','--no-tree','--strict','--no-signoff',str(ref/'early-host-stop.patch')],cwd=k,capture_output=True,text=True)
(out/'checkpatch.txt').write_text(check.stdout+check.stderr);assert check.returncode==0,check.stdout
make('changed-w1',['W=1','-j4','drivers/gpu/drm/msm/dsi/dsi_host.o','drivers/gpu/drm/msm/dsi/dsi_manager.o'])
make('full',['-j4','Image','modules','qcom/sm8150-samurai.dtb'])
assert (k/'.config').read_bytes()==(out/'config-before-private').read_bytes()
image=out/'Image-k157-early-stop-private';assert not image.exists();shutil.copyfile(k/'arch/arm64/boot/Image',image)
assert '#157 SMP PREEMPT' in subprocess.check_output(['strings',str(image)],text=True)
modules=k.parent/'modules-root157';assert not modules.exists();modules.mkdir(mode=0o700)
make('install',['INSTALL_MOD_PATH='+str(modules),'INSTALL_MOD_STRIP=1','modules_install'])
release=(k/'include/config/kernel.release').read_text().strip();(modules/'lib/modules'/release/'build').unlink()
r=subprocess.run(['depmod','-e','-F',str(k/'System.map'),'-b',str(modules),release],capture_output=True)
assert r.returncode==0 and not r.stdout and not r.stderr
def note(data):
    assert data[:6]==b'\x7fELF\x02\x01'
    off=struct.unpack_from('<Q',data,40)[0];size,count,index=struct.unpack_from('<HHH',data,58)
    h=[struct.unpack_from('<IIQQQQIIQQ',data,off+i*size) for i in range(count)]
    strings=data[h[index][4]:h[index][4]+h[index][5]]
    for row in h:
        if strings[row[0]:].split(b'\x00',1)[0]==b'.note.gnu.build-id':return row[4],row[5]
    raise AssertionError('Missing module build ID')
with tarfile.open(out.parent/'kernel132/modules-k132-private.tar.gz') as t:
    old={m.name:t.extractfile(m).read() for m in t if m.isfile() and m.name.endswith('.ko')}
new={str(p.relative_to(modules)):p.read_bytes() for p in modules.rglob('*.ko')}
assert len(new)==len(old)==770 and new.keys()==old.keys()
changed=[]
for n,before in old.items():
    after=new[n]
    if before==after:continue
    a,b=note(before),note(after);assert a==b,(n,a,b)
    pos,size=a
    assert after[:pos]+before[pos:pos+size]+after[pos+size:]==before,n
    changed.append(n)
compat=dict(stage=157,total_modules=770,unchanged_compiled_modules=770-len(changed),build_id_only_differences=changed,
    all_other_bytes_including_code_data_relocations_symbols_and_modinfo_identical=True,existing_modules132_runtime_compatible=True,
    panel_layout_abi_preserved=True,existing_module_files_reused=True,compiled_modules_byte_identical132=not changed)
(ref/'module-compatibility-validation.json').write_text(json.dumps(compat,indent=2)+'\n')
dtb=k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();assert sha(dtb)==base156['dtb_sha256']
target=out/'logdump-k157-early-stop.img';assert not target.exists()
shutil.copyfile(out.parent/'kernel156/logdump-k156-first-frame.img',target)
subprocess.run(['mcopy','-o','-i',str(target),str(image),'::/Image'],check=True)
assert subprocess.check_output(['mcopy','-i',str(target),'::/Image','-'])==image.read_bytes()
assert subprocess.check_output(['mcopy','-i',str(target),'::/samurai.dtb','-'])==dtb.read_bytes()
r=subprocess.run(['fsck.fat','-n',str(target)],capture_output=True);(out/'fat-check.txt').write_bytes(r.stdout+r.stderr)
assert r.returncode==0 and target.stat().st_size==67108864
other=subprocess.check_output(['git','diff','--binary','--','.']+[':(exclude)'+n for n in source['modified_files']],cwd=k)
assert other==(out/'other-diff-before-private.patch').read_bytes()
result=dict(stage=157,kernel_build=157,baseline_kernel=156,software_generation=132,
    image_sha256=sha(image),image_bytes=image.stat().st_size,logdump_sha256=sha(target),logdump_bytes=target.stat().st_size,
    source_sha256=source['after_sha256'],dtb_sha256=sha(dtb),dtb_unchanged=True,
    modules770_byte_identical132=not changed,modules132_runtime_compatible=True,compiled_module_build_id_only_differences=len(changed),
    modules132_reused=True,panel_layout_abi_preserved=True,first_frame156_source_unchanged=True,config_unchanged=True,
    other_tracked_diffs_unchanged=True,build_warnings=0,checkpatch_pass=True,fat_check_pass=True,deployed=False,hardware_bug_fixed=False)
(ref/'build-package-validation.json').write_text(json.dumps(result,indent=2)+'\n')
(out/'build-package-validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result),flush=True)
