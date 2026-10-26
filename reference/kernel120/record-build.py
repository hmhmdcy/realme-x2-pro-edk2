from pathlib import Path
import hashlib,json,subprocess,runpy
runpy.run_path('/mnt/e/RealmeX2Pro edk2/reference/kernel118/ensure-build-volume.py')
k=Path('/home/cy122/pmos-samurai-kernel118/camera120/kernel');base=Path('/home/cy122/pmos-samurai-kernel118/kernel');old=Path('/home/cy122/pmos-samurai-kernel116/kernel')
out=Path('/mnt/e/edk2-samurai-out/kernel120');ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel120')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(base/'arch/arm64/boot/Image')=='57a375cac03605f4d91099ca9994e234ef9dcd043564e1adbc66b4df3ccfa2ab'
assert sha(old/'arch/arm64/boot/Image')=='7ad5e8ffc60c2635649977d1100574574853708a4f6bc39090964a456554f275'
assert (k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts').read_bytes()==(base/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts').read_bytes()
assert (k/'drivers/gpu/drm/msm/disp/dpu1/dpu_hw_ctl.c').read_bytes()==(base/'drivers/gpu/drm/msm/disp/dpu1/dpu_hw_ctl.c').read_bytes()
assert (k/'drivers/net/ipa/reg/ipa_reg-v4.1.c').read_bytes()==(base/'drivers/net/ipa/reg/ipa_reg-v4.1.c').read_bytes()
for p in (old/'drivers/media/platform/qcom/camss').glob('*.[ch]'):assert p.read_bytes()==(k/p.relative_to(old)).read_bytes()
log=(out/'kernel-full-build.log').read_text();assert 'error:' not in log and 'Error ' not in log
assert b'#120 SMP PREEMPT' in subprocess.check_output(['strings',str(k/'vmlinux')])
config=(k/'.config').read_text();assert 'CONFIG_I2C_QCOM_CCI=m\n' in config and 'CONFIG_VIDEO_QCOM_CAMSS=m\n' in config
names=['arch/arm64/boot/Image','arch/arm64/boot/dts/qcom/sm8150-samurai.dtb','drivers/media/platform/qcom/camss/qcom-camss.ko','drivers/i2c/busses/i2c-qcom-cci.ko','drivers/net/ipa/ipa.ko','usr/initramfs_data.cpio']
files={name:sha(k/name) for name in names}
report=dict(candidate=120,full_image_modules_dtb_build_pass=True,cci_module_built=True,camss116_sources_preserved=True,display118_final_read_preserved=True,ipa_tx_delay_fix_preserved=True,board_dts_byte_identical_to118=True,baseline116_and118_images_preserved=True,module_count=sum(1 for p in k.rglob('*.ko')),image_and_module_hashes=files,not_deployed=True,rootfs115_not_claimed_compatible_with120_modules=True,goal_complete=False)
for folder in [out,ref]:(folder/'kernel-build-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
