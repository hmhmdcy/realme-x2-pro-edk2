from pathlib import Path
import hashlib, json, shutil, gzip, tarfile, subprocess

k=Path('/home/cy122/x2pro-linux/linux')
r=Path('/home/cy122/edk2-samurai/repo')
out=Path('/mnt/e/edk2-samurai-out/kernel75')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel75')
sha=lambda b: hashlib.sha256(b).hexdigest()
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=r,text=True).strip()=='20a1d6041b0f4a5b3eb384372de65c22ff2ab81e'
assert not subprocess.check_output(['git','status','--porcelain'],cwd=r)
previous=json.loads((ref.parent/'kernel74/sources-before.json').read_text())
core=list(previous)
state={}
for n in core:
    src=Path('/home/cy122/x2pro-linux/initramfs')/('init' if n=='init' else 'usr/sbin/samurai-usb') if n in ('init','samurai-usb') else k/n
    state[n]=sha(src.read_bytes())
    if 'dpu1/' not in n: assert state[n]==previous[n],n
    else: assert src.read_bytes()==(ref.parent/'kernel74'/(src.name+'.after')).read_bytes(),n
assert sha((k/'.config').read_bytes())=='9d9f10ae4a96e4a0575b7c51d818180a68e596e84898a3849fe1183307223c6d'
for symbol in ('DRM_MSM','DRM_SCHED','SM_GPUCC_8150','ARM_SMMU','QCOM_SCM','QCOM_MDT_LOADER','QCOM_LLCC','QCOM_GDSC','QCOM_RPMHPD','PM_DEVFREQ','INTERCONNECT_QCOM_SM8150','FW_LOADER'):
    assert ('CONFIG_'+symbol+'=y') in (k/'.config').read_text(),symbol
assert 'CONFIG_DRM_MSM_GPU_SUDO=y' not in (k/'.config').read_text()
backups={
 'Image-before': k/'arch/arm64/boot/Image', 'config-before':k/'.config',
 'dtb-before': k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb',
 'dts-before': k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts',
 'logdump-before.img':out.parent/'kernel74/logdump-k74-drain.img',
 'boot-before.img':r/'boot-samurai.img',
 'firmware-before.dtb':r/'Platform/Realme/sm8150/FdtBlob/samurai/sm8150-realme-samurai.dtb',
 'compat-before.dtb':r/'Platform/Realme/sm8150/FdtBlob_compat/samurai.dtb',
}
for target,source in backups.items():
    assert not (out/target).exists(),target
    shutil.copyfile(source,out/target)
fv=r/'workspace/Build/samurai/RELEASE_GCC5/FV'
for target,source in {'firmware-before.fd':'SM8150_UEFI.fd','fvmain-before.Fv':'FVMAIN.Fv','fvcompact-before.Fv':'FVMAIN_COMPACT.Fv'}.items():
    assert not (out/target).exists()
    shutil.copyfile(fv/source,out/target)
assert sha((out/'Image-before').read_bytes())=='a08dc7fb1061d00f09a48d1a9eccbe3e5c2e165fce22d4f94ccd2432faafe0a7'
assert sha((out/'logdump-before.img').read_bytes())=='8e43d13658a1d332c441f68a6008e7ebb855177b59fbeb447a196195239f1ee5'
assert sha((out/'boot-before.img').read_bytes())=='57508887131ae55cf9465fa1a44280fa45b507a3439345ffe635dc7544eaa999'
(ref/'sources-before.json').write_text(json.dumps(state,indent=2)+'\n')
raw=gzip.decompress((out/'before-dmesg.gz').read_bytes())
assert sha(raw)=='410a922ebf761df20d0104c720bc54d7f95c03faf4f2dacf8db6a287885682f0'
(ref/'before-dmesg.txt').write_bytes(raw)
shutil.copyfile(out/'before-dmesg.gz',ref/'before-dmesg.gz')

subprocess.run(['python3',str(ref.parent/'kernel74/verify-gpu-firmware.py')],check=True)
manifest=json.loads((ref.parent/'kernel73/gpu-firmware-manifest.json').read_text())
installed={}
with tarfile.open(out.parent/'kernel73/gpu-firmware-stock.tar') as tar:
    for name,target in {'a630_sqe.fw':'qcom/a630_sqe.fw','a640_gmu.bin':'qcom/a640_gmu.bin','a640_zap.elf':'qcom/sm8150/realme/samurai/a640_zap.mbn'}.items():
        raw=tar.extractfile(name).read()
        assert sha(raw)==manifest['files'][name]['sha256']
        dest=Path('/home/cy122/x2pro-linux/initramfs/lib/firmware')/target
        assert not dest.exists(),target
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes(raw); dest.chmod(0o644)
        installed[target]={'bytes':len(raw),'sha256':sha(raw),'source_stock_name':name}
(ref/'gpu-installed-manifest.json').write_text(json.dumps(installed,indent=2)+'\n')
p=k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts'
s=p.read_text()
old='''/*
 * Bring-up scope.  None of the below is known to work on mainline yet, and
 * all of it needs firmware that a RAM-only userspace cannot supply, so keep
 * it out of the first boots.
 */
&gmu {
\tstatus = "disabled";
};

&gpu {
\tstatus = "disabled";
};
'''
new='''/* Adreno firmware is supplied by the initramfs from this handset's vendor. */
&gmu {
\tstatus = "okay";
};

&gpu {
\tstatus = "okay";
};

&gpu_zap_shader {
\tfirmware-name = "qcom/sm8150/realme/samurai/a640_zap.mbn";
};

/* Remaining firmware-dependent peripherals are brought up separately. */
'''
assert s.count(old)==1
p.write_text(s.replace(old,new))
for name in ('reboot-f1.ps1','reboot-ready-fastboot.ps1','validate-initramfs.py','run-drain-tests.sh','run-drain-reboot-tests.sh'):
    src=ref.parent/'kernel74'/name
    (ref/name).write_text(src.read_text().replace('kernel74','kernel75').replace('k74','k75'))
print('Baseline #68 backed up; three own-device firmware files installed; GPU/GMU enabled with board-specific ZAP path.')
