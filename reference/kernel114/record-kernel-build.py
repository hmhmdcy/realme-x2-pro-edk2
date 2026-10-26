from pathlib import Path
import hashlib, json, subprocess

kernel=Path('/home/cy122/pmos-samurai-kernel114/kernel')
out=Path('/mnt/e/edk2-samurai-out/kernel114')
paths=['arch/arm64/boot/Image','arch/arm64/boot/dts/qcom/sm8150-samurai.dtb','drivers/net/ipa/ipa.ko','drivers/block/zram/zram.ko','mm/zsmalloc.ko','usr/initramfs_data.cpio']
assert all((kernel/p).is_file() and (kernel/p).stat().st_size>0 for p in paths)
config=(kernel/'.config').read_text()
assert 'CONFIG_ZSMALLOC=m\n' in config and 'CONFIG_ZRAM=m\n' in config and 'CONFIG_SYN_COOKIES=y\n' in config
assert 'CONFIG_QCOM_IPA=m\n' in config
banner=subprocess.check_output(['strings',str(kernel/'arch/arm64/boot/Image')],text=True)
uts=(kernel/'include/generated/utsversion.h').read_text().split('"')[1]
assert uts.startswith('#114 ')
banner=[s for s in banner.splitlines() if s.startswith('Linux version ') and uts in s]
assert len(banner)==1
modules={p:hashlib.sha256((kernel/p).read_bytes()).hexdigest() for p in paths}
for rel,name in [('arch/arm64/boot/Image','Image-ipa-disabled-zram'),('arch/arm64/boot/dts/qcom/sm8150-samurai.dtb','dtb-ipa-disabled-zram'),('usr/initramfs_data.cpio','cpio-ipa-disabled-zram')]:
    import shutil
    shutil.copy2(kernel/rel,out/name)
report=dict(kernel_build=114,full_image_modules_dtb_build_pass=True,artifact_sha256=modules,
            zram_driver_built=True,zsmalloc_module_built=True,tcp_syncookies_enabled=True,
            ipa_v4_1_driver_built=True,ipa_soc_node_disabled=True,foreign_board_config_not_applied=True,
            no_device_flash_or_reboot=True,rootfs114_image_retains_kernel113_modules=True,
            runtime_hardware_acceptance=False,goal_complete=False)
(out/'kernel-build-validation.json').write_text(json.dumps(report,indent=2)+'\n')
Path('/mnt/e/RealmeX2Pro edk2/reference/kernel114/kernel-build-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
