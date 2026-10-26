from pathlib import Path
import subprocess,hashlib,json,tempfile
old=Path('/home/cy122/pmos-samurai-kernel115/kernel')
k=Path('/home/cy122/pmos-samurai-kernel118/kernel')
out=Path('/mnt/e/edk2-samurai-out/kernel118')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel118')
subprocess.run(['python3',str(ref/'ensure-build-volume.py')],check=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert (k/'include/generated/utsversion.h').read_text().split('"')[1].startswith('#118 ')
assert (old/'include/generated/utsversion.h').read_text().split('"')[1].startswith('#115 ')
assert sha(old/'arch/arm64/boot/Image')=='66e749a8e9902c5675af736706c193b645d7e1ab49f71980e5c0c652db45bfa2'
assert (old/'include/config/kernel.release').read_bytes()==(k/'include/config/kernel.release').read_bytes()
assert (old/'.config').read_text().replace('/kernel115/','/kernel118/').replace('-kernel115/','-kernel118/')==(k/'.config').read_text()
scope=['--','.',':(exclude)drivers/gpu/drm/msm/disp/dpu1/dpu_hw_ctl.c']
diff=lambda tree:subprocess.check_output(['git','diff','--binary',*scope],cwd=tree)
assert diff(old)==diff(k),'other tracked-source changes'
subprocess.run(['git','diff','--check','--','drivers/gpu/drm/msm/disp/dpu1/dpu_hw_ctl.c'],cwd=k,check=True)
dtb='arch/arm64/boot/dts/qcom/sm8150-samurai.dtb'
assert sha(k/dtb)==sha(old/dtb)=='f3e970e5967c4f6768b3b8e2b54dad833a7a7f532eb6ae856093c3c1514877da'
def exports(tree):
    records=[tuple(l.split()) for l in (tree/'Module.symvers').read_text().splitlines()]
    assert len(records)==len(set(records))
    return set(records)
abi_old=exports(old);abi_new=exports(k)
assert all(r[2]=='vmlinux' for r in abi_old),'unexpected baseline symvers scope'
assert {r for r in abi_new if r[2]=='vmlinux'}==abi_old,'built-in export differs'
modules=list(k.rglob('*.ko'));assert len(modules)==len(list(old.rglob('*.ko')))
with tempfile.TemporaryDirectory(prefix='samurai-k118-module-check-') as temp:
    temp=Path(temp)
    for module in modules:
        rel=module.relative_to(k)
        for tree,name in [(old,'old.ko'),(k,'new.ko')]:
            subprocess.run(['aarch64-linux-gnu-strip','--strip-debug','--remove-section=.note.gnu.build-id','-o',str(temp/name),str(tree/rel)],check=True)
        assert (temp/'old.ko').read_bytes()==(temp/'new.ko').read_bytes(),f'loadable module differs: {rel}'
vermagic=lambda tree,rel:subprocess.check_output(['modinfo','-F','vermagic',str(tree/rel)],text=True).strip()
for rel in ['drivers/net/ipa/ipa.ko','drivers/block/zram/zram.ko','mm/zsmalloc.ko']:
    assert vermagic(k,rel)==vermagic(old,rel)
assert 'ENDP_INIT_CTRL' in (k/'drivers/net/ipa/reg/ipa_reg-v4.1.c').read_text()
assert sha(k/'drivers/net/ipa/reg/ipa_reg-v4.1.c')==sha(old/'drivers/net/ipa/reg/ipa_reg-v4.1.c')
init=lambda tree:{str(p.relative_to(tree)):sha(p) for p in tree.rglob('*') if p.is_file() and not p.is_symlink()}
assert init(k.parent/'initramfs')==init(old.parent/'initramfs')
def cpio_members(tree):
    data=(tree/'usr/initramfs_data.cpio').read_bytes();offset=0;members={}
    while True:
        assert data[offset:offset+6]==b'070701'
        fields=[int(data[offset+6+i*8:offset+14+i*8],16) for i in range(13)]
        offset+=110
        name=data[offset:offset+fields[11]-1].decode();offset=(offset+fields[11]+3)&~3
        body=data[offset:offset+fields[6]];offset=(offset+fields[6]+3)&~3
        if name=='TRAILER!!!':break
        assert name not in members
        members[name]=(fields[1],fields[2],fields[3],fields[9],fields[10],hashlib.sha256(body).hexdigest())
    return members
assert cpio_members(old)==cpio_members(k),'embedded initramfs semantic contents differ'
paths=['arch/arm64/boot/Image',dtb,'drivers/net/ipa/ipa.ko','usr/initramfs_data.cpio','Module.symvers']
report=dict(candidate=118,base=115,full_image_modules_dtb_build_pass=True,only_one_tracked_source_file_differs=True,config_semantically_identical=True,dtb_byte_identical=True,exported_module_abi_identical=True,baseline_symvers_builtin_only=True,baseline_vmlinux_exports_identical=True,all_stripped_module_bytes_identical_excluding_build_id=True,modversions_disabled=True,export_records=len(abi_new),module_count=len(modules),sample_vermagic_identical=True,ipa_delay_fix_preserved=True,initramfs_inputs_identical=True,embedded_cpio_semantically_identical=True,baseline_115_preserved=True,artifact_sha256={p:sha(k/p) for p in paths},not_deployed=True,device_runtime_acceptance=False,goal_complete=False)
for folder in [out,ref]: (folder/'kernel-build-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
