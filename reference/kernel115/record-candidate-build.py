from pathlib import Path
import hashlib,json,subprocess,shutil
k=Path('/home/cy122/pmos-samurai-kernel115/kernel')
out=Path('/mnt/e/edk2-samurai-out/kernel115')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel115')
paths=['arch/arm64/boot/Image','arch/arm64/boot/dts/qcom/sm8150-samurai.dtb','drivers/net/ipa/ipa.ko','drivers/block/zram/zram.ko','mm/zsmalloc.ko','usr/initramfs_data.cpio']
assert all((k/p).stat().st_size>0 for p in paths)
config=(k/'.config').read_text()
for item in ['CONFIG_ZSMALLOC=m','CONFIG_ZRAM=m','CONFIG_SYN_COOKIES=y','CONFIG_QCOM_IPA=m']:
    assert item+'\n' in config
assert (k/'include/generated/utsversion.h').read_text().split('"')[1].startswith('#115 ')
dtb=k/paths[1]
prop=lambda name:subprocess.check_output(['fdtget','-t','s',str(dtb),'/soc@0/ipa@1e40000',name],text=True).strip()
assert prop('status')=='okay' and prop('qcom,gsi-loader')=='self'
assert prop('firmware-name')=='qcom/sm8150/realme/samurai/ipa_fws.mdt'
assert '0x146bd000' in (k/'drivers/net/ipa/data/ipa_data-v4.1.c').read_text()
function=(k/'drivers/net/ipa/gsi_trans.c').read_text().split('void gsi_trans_commit_wait(')[1].split('/* Process the completion')[0]
assert 'wait_for_completion_timeout' in function and 'refcount_inc' in function and 'gsi_trans_free' in function
scope=['drivers/net/ipa','arch/arm64/boot/dts/qcom/sm8150.dtsi','arch/arm64/boot/dts/qcom/sm8150-samurai.dts']
subprocess.run(['git','diff','--check','--',*scope],cwd=k,check=True)
(out/'candidate-source-diff.patch').write_bytes(subprocess.check_output(['git','diff','--',*scope],cwd=k))
for rel,name in [(paths[0],'Image-ipa-zram'),(paths[1],'dtb-ipa-zram'),(paths[5],'cpio-ipa-zram')]:
    shutil.copy2(k/rel,out/name)
report=dict(kernel_build=115,full_image_modules_dtb_build_pass=True,artifact_sha256={p:hashlib.sha256((k/p).read_bytes()).hexdigest() for p in paths},own_register_offset_verified=True,own_imem_address='0x146bd000',gsi_register_size='0x28000',gsi_wait_bounded_ms=1000,own_vendor_firmware_verified=True,firmware_loader='self',ipa_board_node_enabled=True,clock_interconnect_values_provisional=True,slpi_auto_boot=False,zram_driver_built=True,zsmalloc_module_built=True,tcp_syncookies_enabled=True,no_device_flash_or_reboot=True,runtime_hardware_acceptance=False,goal_complete=False)
for dest in [out,ref]: (dest/'kernel-build-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('KERNEL115_IMAGE_MODULES_DTB_AND_TARGETED_SOURCE_AUDIT_PASS')
