from pathlib import Path
import hashlib,json,shutil,struct,subprocess,tarfile
k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
out=Path('/mnt/e/edk2-samurai-out/kernel156')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel156')
source=json.loads((ref/'source-validation.json').read_text())
for n,sha in source['after_sha256'].items():assert hashlib.sha256((k/n).read_bytes()).hexdigest()==sha,n
assert (k/'.config').read_bytes()==(out/'config-before-private').read_bytes()
for label in ['changed-w1-retry1','full','install']:
    log=(out/(label+'-build-private.log')).read_text()
    assert 'error:' not in log and 'warning:' not in log,label
assert json.loads((ref/'panel-layout-validation.json').read_text())['struct_size_preserved']
def note(data):
    assert data[:6]==b'\x7fELF\x02\x01'
    off=struct.unpack_from('<Q',data,40)[0];size,count,index=struct.unpack_from('<HHH',data,58)
    headers=[struct.unpack_from('<IIQQQQIIQQ',data,off+i*size) for i in range(count)]
    strings=data[headers[index][4]:headers[index][4]+headers[index][5]]
    for h in headers:
        name=strings[h[0]:].split(b'\x00',1)[0]
        if name==b'.note.gnu.build-id':return h[4],h[5]
    raise AssertionError('Missing build ID note')
modules=k.parent/'modules-root156'
with tarfile.open(out.parent/'kernel132/modules-k132-private.tar.gz') as tar:
    old={m.name:tar.extractfile(m).read() for m in tar if m.isfile() and m.name.endswith('.ko')}
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
assert len(changed)==2,changed
compat=dict(stage=156,total_modules=770,unchanged_compiled_modules=768,
    build_id_only_differences=changed,all_other_bytes_including_code_data_relocations_symbols_and_modinfo_identical=True,
    existing_modules132_runtime_compatible=True,panel_layout_abi_preserved=True,
    existing_module_files_reused=True,compiled_modules_byte_identical132=False)
(ref/'module-compatibility-validation.json').write_text(json.dumps(compat,indent=2)+'\n')
image=out/'Image-k156-first-frame-private'
assert image.read_bytes()==(k/'arch/arm64/boot/Image').read_bytes()
assert '#156 SMP PREEMPT' in subprocess.check_output(['strings',str(image)],text=True)
dtb=k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(dtb)==json.loads((ref.parent/'kernel154/build-package-validation.json').read_text())['dtb_sha256']
target=out/'logdump-k156-first-frame.img';assert not target.exists()
shutil.copyfile(out.parent/'kernel154/logdump-k154-host-init.img',target)
subprocess.run(['mcopy','-o','-i',str(target),str(image),'::/Image'],check=True)
assert subprocess.check_output(['mcopy','-i',str(target),'::/Image','-'])==image.read_bytes()
assert subprocess.check_output(['mcopy','-i',str(target),'::/samurai.dtb','-'])==dtb.read_bytes()
r=subprocess.run(['fsck.fat','-n',str(target)],capture_output=True)
(out/'fat-check.txt').write_bytes(r.stdout+r.stderr)
assert r.returncode==0 and target.stat().st_size==67108864
other=subprocess.check_output(['git','diff','--binary','--','.']+[':(exclude)'+n for n in source['modified_files']],cwd=k)
assert other==(out/'other-diff-before-private.patch').read_bytes()
result=dict(stage=156,kernel_build=156,baseline_kernel=154,software_generation=132,
    image_sha256=sha(image),image_bytes=image.stat().st_size,logdump_sha256=sha(target),logdump_bytes=target.stat().st_size,
    source_sha256=source['after_sha256'],dtb_sha256=sha(dtb),dtb_unchanged=True,
    modules770_byte_identical132=False,modules132_runtime_compatible=True,compiled_module_build_id_only_differences=2,
    modules132_reused=True,panel_layout_abi_preserved=True,config_unchanged=True,other_tracked_diffs_unchanged=True,
    build_warnings=0,checkpatch_pass=True,checkpatch_ignored_types=['OPEN_ENDED_LINE'],
    valid_trace_macro_delimiters=True,fat_check_pass=True,deployed=False,hardware_bug_fixed=False)
(ref/'build-package-validation.json').write_text(json.dumps(result,indent=2)+'\n')
(out/'build-package-validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result),flush=True)
